from datetime import time as clock

import streamlit as st

# Bring the logic-layer classes into the UI.
from pawpal_system import Owner, Pet, Scheduler, Task

# Bring the AI (RAG) layer into the UI.
from pawpal_ai import PetCareAdvisor, configure_logging

configure_logging()  # write a pawpal.log audit trail of retrieval + generation

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan the day's pet care around the time you have.")

# Application memory. Streamlit reruns this whole script on every interaction,
# so we keep the Owner (with its pets and tasks) in st.session_state instead of
# rebuilding it. One shared Scheduler runs the smart logic.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan", available_minutes=90)

owner: Owner = st.session_state.owner
scheduler = Scheduler()

# The RAG advisor loads its knowledge base once and is reused across reruns.
if "advisor" not in st.session_state:
    st.session_state.advisor = PetCareAdvisor()
advisor: PetCareAdvisor = st.session_state.advisor

st.divider()

# --- Owner + time budget -----------------------------------------------------
st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)
owner.available_minutes = st.number_input(
    "Time available today (minutes)",
    min_value=0,
    max_value=1440,
    value=owner.available_minutes,
    step=15,
)

st.divider()

# --- Add a pet ---------------------------------------------------------------
st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    new_pet_name = st.text_input("Pet name", value="")
    c1, c2 = st.columns(2)
    with c1:
        new_species = st.selectbox("Species", ["dog", "cat", "other"])
    with c2:
        new_breed = st.text_input("Breed", value="")
    add_pet_clicked = st.form_submit_button("Add pet")

if add_pet_clicked:
    if new_pet_name.strip():
        owner.add_pet(Pet(new_pet_name.strip(), species=new_species, breed=new_breed.strip()))
        st.success(f"Added {new_pet_name.strip()}.")
    else:
        st.warning("Please enter a pet name.")

if not owner.pets:
    st.info("No pets yet. Add one above to start planning.")

# --- Add a task to a pet -----------------------------------------------------
if owner.pets:
    st.divider()
    st.subheader("Add a task")
    with st.form("add_task", clear_on_submit=True):
        target_pet_name = st.selectbox("For which pet?", [p.name for p in owner.pets])
        task_desc = st.text_input("Task", value="")
        d1, d2 = st.columns(2)
        with d1:
            task_time = st.time_input("Time", value=clock(8, 0))
        with d2:
            task_duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        d3, d4 = st.columns(2)
        with d3:
            task_priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with d4:
            task_frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
        add_task_clicked = st.form_submit_button("Add task")

    if add_task_clicked:
        if task_desc.strip():
            pet = owner.find_pet(target_pet_name)
            pet.add_task(
                Task(
                    task_desc.strip(),
                    duration=int(task_duration),
                    priority=task_priority,
                    frequency=task_frequency,
                    time=task_time.strftime("%H:%M"),
                )
            )
            st.success(f"Added '{task_desc.strip()}' for {pet.name} at {task_time:%H:%M}.")
        else:
            st.warning("Please enter a task description.")

    # --- Task list with filters + completion toggles -------------------------
    st.divider()
    st.subheader("Tasks")
    f1, f2 = st.columns(2)
    with f1:
        pet_filter = st.selectbox("Show pet", ["All"] + [p.name for p in owner.pets])
    with f2:
        hide_done = st.checkbox("Hide completed", value=False)

    for pet in owner.pets:
        if pet_filter != "All" and pet.name != pet_filter:
            continue
        label = pet.name + (f" ({pet.breed})" if pet.breed else "")
        st.markdown(f"**{label}**")
        visible = [t for t in pet.tasks if not (hide_done and t.completed)]
        if not visible:
            st.caption("No tasks to show.")
        for task in visible:
            checked = st.checkbox(str(task), value=task.completed, key=f"done_{task.id}")
            # Only act on the transition so recurring tasks regenerate once.
            if checked and not task.completed:
                upcoming = scheduler.mark_task_complete(owner, task.id)
                if upcoming is not None:
                    st.session_state.recurred = f"'{upcoming.description}' re-added for {upcoming.due_date}."
                st.rerun()
            elif not checked and task.completed:
                task.mark_incomplete()

    if "recurred" in st.session_state:
        st.success("🔁 " + st.session_state.pop("recurred"))

st.divider()

# --- Today's schedule: conflicts, agenda, and the auto-fit plan --------------
if owner.pets:
    st.subheader("Today's Schedule")

    # Conflict warnings shown prominently so the owner can fix double-bookings.
    conflicts = scheduler.detect_conflicts(owner)
    for warning in conflicts:
        st.warning("⚠️ " + warning)
    if not conflicts:
        st.success("No scheduling conflicts. ✅")

    # Agenda sorted by the times the owner set (uses sort_by_time + filter_tasks).
    pending = owner.pending_tasks()
    if pending:
        pet_by_id = {task.id: pet for pet, task in pending}
        ordered = scheduler.sort_by_time([task for _pet, task in pending])
        st.markdown("**Agenda (by time)**")
        st.table(
            [
                {
                    "Time": task.time or "—",
                    "Task": task.description,
                    "Pet": pet_by_id[task.id].name,
                    "Priority": task.priority,
                    "Duration": f"{task.duration} min",
                    "Repeats": task.frequency,
                }
                for task in ordered
            ]
        )
    else:
        st.info("No pending tasks. Add one above to build an agenda.")

    # Priority-first auto-fit plan within the available time budget.
    if st.button("Auto-fit plan for my available time", type="primary"):
        plan = scheduler.build_plan(owner)
        if plan["scheduled"]:
            st.table(
                [
                    {
                        "Start": f"{entry['start']:%H:%M}",
                        "End": f"{entry['end']:%H:%M}",
                        "Task": entry["task"].description,
                        "Pet": entry["pet"].name,
                        "Priority": entry["task"].priority,
                        "Min": entry["task"].duration,
                    }
                    for entry in plan["scheduled"]
                ]
            )
        else:
            st.info("Nothing could be scheduled. Add tasks or increase the available time.")

        if plan["skipped"]:
            st.markdown("**Skipped (ran out of time):**")
            for entry in plan["skipped"]:
                st.write(f"- {entry['task'].description} for {entry['pet'].name}")

        st.caption(plan["reasoning"])

# --- AI Advisor (RAG): grounded care advice for a chosen pet -----------------
if owner.pets:
    st.divider()
    st.subheader("🤖 PawPal Advisor")
    st.caption(
        "Retrieves real pet-care guidelines, then asks an AI to turn them into "
        "advice for this pet's actual tasks and your time budget."
    )

    advice_pet_name = st.selectbox(
        "Advise on which pet?", [p.name for p in owner.pets], key="advice_pet"
    )
    if st.button("Get care advice", key="advise_button"):
        pet = owner.find_pet(advice_pet_name)
        # Describe the pet's pending tasks so the AI grounds advice in the real plan.
        task_lines = [
            f"{t.description} — {t.duration} min, {t.priority} priority, "
            f"at {t.time or 'unscheduled'}, repeats {t.frequency}"
            for t in pet.pending_tasks()
        ]
        pet_label = f"{pet.name} ({pet.breed or pet.species or 'pet'})"
        with st.spinner("Retrieving guidelines and generating advice…"):
            result = advisor.advise(
                pet_label=pet_label,
                species=pet.species,
                breed=pet.breed,
                task_descriptions=task_lines,
                available_minutes=owner.available_minutes,
            )

        st.markdown(result.advice)

        # Show which backend answered and which guidelines grounded the advice —
        # transparency that this is retrieval-augmented, not made up.
        backend_labels = {
            "anthropic": "Anthropic API",
            "ollama": "local Ollama model",
            "offline": "offline fallback (no live model)",
        }
        st.caption(f"Generated by: {backend_labels.get(result.backend, result.backend)}")
        if result.sources:
            with st.expander("📚 Guidelines used (retrieved from the knowledge base)"):
                for src in result.sources:
                    st.write(f"- {src}")
