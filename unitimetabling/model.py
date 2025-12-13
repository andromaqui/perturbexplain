from ortools.sat.python import cp_model
from itertools import combinations

# 7 days
# labs start from 8AM to 5PM
# labs last only 1 hour
# there is an old schedule and you should try to change a given time

CLASS_DURATION = 60  # minutes
NUM_TIME_SLOTS = 9 * 60
NUM_DAYS = 7
NUM_ROOMS = 3
OLDPLAN = {
    "labs": {
        "machinelearning": {"day": 1, "start": 60, "room": "GPUA", "locked": False},
        "computervision": {"day": 1, "start": 180, "room": "GPUB", "locked": True},
        "cloudcomputing": {"day": 2, "start": 120, "room": "LINUX", "locked": True},
        "workshopinai": {"day": 5, "start": 240, "room": "GPUA", "locked": False},
    }
}
TOCHANGE = "workshopinai"


def make_problem_data():

    lab_lecturer = {
        "machinelearning": "alice",
        "computervision": "alice",
        "cloudcomputing": "bob",
        "workshopinai": "workshopperson"
    }

    lab_to_studentIds = {
        "machinelearning": [1, 2, 3, 4, 5, 6, 7, 8, 1333],
        "computervision": [1, 2, 3, 4, 5, 6, 7, 8],
        "cloudcomputing": [1, 2, 3, 4, 5, 6, 7, 18],
        "workshopinai": [12, 15, 18],
    }

    lecturer_forbidden = {
        "alice": [(0, 0)],
        "bob": [(1, 0), (1, 3)],
        "workshopperson": [(0, -1)]
    }

    lab_day = {
        "workshopinai": [5, 6]
    }

    labs = ["machinelearning", "computervision", "cloudcomputing", "workshopinai"]
    rooms = ["LINUX", "GPUA", "GPUB"]

    allowed_rooms = {
        "machinelearning": ["GPUA", "GPUB"],
        "cloudcomputing": ["LINUX"],
        "computervision": ["GPUA", "GPUB"],
        "workshopinai": ["GPUA", "GPUB"]
    }

    room_distance = {
        ("GPUA", "GPUB"): 2,
        ("GPUA", "LINUX"): 10,
        ("GPUB", "LINUX"): 8,
    }

    rooms_to_classes = {
        "GPUA": ["machinelearning", "computervision", "workshopinai"],
        "GPUB": ["machinelearning", "computervision"],
        "LINUX": ["cloudcomputing"],
    }

    return {
        "NUM_TIME_SLOTS": NUM_TIME_SLOTS,
        "NUM_DAYS": NUM_DAYS,
        "NUM_ROOMS": NUM_ROOMS,
        "lab_lecturer": lab_lecturer,
        "lab_to_studentIds": lab_to_studentIds,
        "lecturer_forbidden": lecturer_forbidden,
        "lab_day": lab_day,
        "labs": labs,
        "rooms": rooms,
        "allowed_rooms": allowed_rooms,
        "room_distance": room_distance,
        "rooms_to_classes": rooms_to_classes,
    }


def find_lab_studentintersections(data):
    lab_to_studentIds = data["lab_to_studentIds"]
    lab_sets = {lab: set(ids) for lab, ids in lab_to_studentIds.items()}
    conflicts = {lab: [] for lab in lab_sets}

    for lab1, lab2 in combinations(lab_sets.keys(), 2):
        if lab_sets[lab1] & lab_sets[lab2]:
            conflicts[lab1].append(lab2)
            conflicts[lab2].append(lab1)

    return conflicts


def build_model(data):
    model = cp_model.CpModel()

    NUM_TIME_SLOTS = data["NUM_TIME_SLOTS"]
    NUM_DAYS = data["NUM_DAYS"]
    NUM_ROOMS = data["NUM_ROOMS"]

    lab_lecturer = data["lab_lecturer"]
    lecturer_forbidden = data["lecturer_forbidden"]
    lab_day = data["lab_day"]
    labs = data["labs"]
    rooms_to_classes = data["rooms_to_classes"]

    day_slots = list(range(NUM_DAYS))
    room_slots = list(range(NUM_ROOMS))

    GPUA = 0
    GPUB = 1
    LINUX = 2
    SLOTS_PER_DAY = NUM_TIME_SLOTS  # 9*60

    time_vars = {}
    day_vars = {}
    slot_vars = {}
    room_vars = {}
    is_on_GPUA = {}
    is_on_GPUB = {}

    linux_vars = []

    for lab in labs:
        hour_var = model.NewIntVar(0, 8, "hour_" + lab)
        minute_var = model.NewIntVar(0, NUM_TIME_SLOTS - 1, "time_" + lab)
        model.Add(minute_var == hour_var * 60)

        time_vars[lab] = minute_var
        day_vars[lab] = model.NewIntVar(0, len(day_slots) - 1, "day_" + lab)
        slot_vars[lab] = model.NewIntVar(0, NUM_DAYS * SLOTS_PER_DAY - 1, f"slot_{lab}")
        model.Add(slot_vars[lab] == day_vars[lab] * SLOTS_PER_DAY + time_vars[lab])

        model.Add(time_vars[lab] != 4 * 60)

        if lab in lab_day:
            model.AddAllowedAssignments([day_vars[lab]], [(d,) for d in lab_day[lab]])

        lec = lab_lecturer[lab]
        if lec in lecturer_forbidden:
            for day, slot in lecturer_forbidden[lec]:
                if slot == -1:
                    for s in range(SLOTS_PER_DAY):
                        model.Add(day_vars[lab] != day)
                else:
                    model.AddForbiddenAssignments([day_vars[lab], time_vars[lab]], [(day, slot)])

        if lab in rooms_to_classes["GPUA"] or lab in rooms_to_classes["GPUB"]:
            room_vars[lab] = model.NewIntVar(0, len(room_slots) - 2, "room_" + lab)

            is_on_GPUA[lab] = model.NewBoolVar("is_on_GPUA_" + lab)
            is_on_GPUB[lab] = model.NewBoolVar("is_on_GPUB_" + lab)

            model.Add(room_vars[lab] == GPUA).OnlyEnforceIf(is_on_GPUA[lab])
            model.Add(room_vars[lab] == GPUB).OnlyEnforceIf(is_on_GPUB[lab])
            model.Add(is_on_GPUA[lab] + is_on_GPUB[lab] == 1)
        else:
            room_vars[lab] = model.NewIntVar(LINUX, LINUX, "room_" + lab)
            linux_vars.append(time_vars[lab])


    apply_old_plan_constraints_up_to_one_change(
        model,
        labs,
        time_vars,
        day_vars,
        room_vars,
        OLDPLAN,
        TOCHANGE,
    )

    # 1 hour after the other
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            lab_i = labs[i]
            lab_j = labs[j]

            same = model.NewBoolVar("same_room_" + lab_i + "_" + lab_j)
            model.Add(room_vars[lab_i] == room_vars[lab_j]).OnlyEnforceIf(same)
            model.Add(room_vars[lab_i] != room_vars[lab_j]).OnlyEnforceIf(same.Not())

            before = model.NewBoolVar("before_" + lab_i + "_" + lab_j)
            model.Add(time_vars[lab_i] + 60 <= time_vars[lab_j]).OnlyEnforceIf([same, before])
            model.Add(time_vars[lab_j] + 60 <= time_vars[lab_i]).OnlyEnforceIf([same, before.Not()])

    labStudentIntersections = find_lab_studentintersections(data)

    for lab in labStudentIntersections:
        for other_lab in labStudentIntersections[lab]:
            if lab >= other_lab:
                continue

            b = model.NewBoolVar(f"no_overlap_{lab}_{other_lab}")
            model.Add(slot_vars[lab] + CLASS_DURATION <= slot_vars[other_lab]).OnlyEnforceIf(b)
            model.Add(slot_vars[other_lab] + CLASS_DURATION <= slot_vars[lab]).OnlyEnforceIf(b.Not())

    return model, time_vars, day_vars, room_vars


def apply_old_plan_constraints(
    model,
    lab,
    time_vars,
    day_vars,
    room_vars,
    OLDPLAN,
    TOCHANGE,
):
    oldLabData = OLDPLAN["labs"][lab]

    if lab != TOCHANGE:
        model.Add(time_vars[lab] == oldLabData["start"])
        model.Add(day_vars[lab] == oldLabData["day"])

        if oldLabData["room"] == "GPUA":
            model.Add(room_vars[lab] == 0)
        elif oldLabData["room"] == "GPUB":
            model.Add(room_vars[lab] == 1)
        elif oldLabData["room"] == "LINUX":
            model.Add(room_vars[lab] == 2)

    else:
        model.AddForbiddenAssignments(
            [day_vars[lab], time_vars[lab]],
            [(5, 240)],
        )



def apply_old_plan_constraints_up_to_one_change(
    model,
    labs,
    time_vars,
    day_vars,
    room_vars,
    OLDPLAN,
    TOCHANGE,
):
    changed = {}

    for lab in labs:
        old = OLDPLAN["labs"][lab]

        old_room_idx = {"GPUA": 0, "GPUB": 1, "LINUX": 2}[old["room"]]

        diff_time = model.NewBoolVar("diff_time_" + lab)
        model.Add(time_vars[lab] != old["start"]).OnlyEnforceIf(diff_time)
        model.Add(time_vars[lab] == old["start"]).OnlyEnforceIf(diff_time.Not())

        diff_day = model.NewBoolVar("diff_day_" + lab)
        model.Add(day_vars[lab] != old["day"]).OnlyEnforceIf(diff_day)
        model.Add(day_vars[lab] == old["day"]).OnlyEnforceIf(diff_day.Not())

        diff_room = model.NewBoolVar("diff_room_" + lab)
        model.Add(room_vars[lab] != old_room_idx).OnlyEnforceIf(diff_room)
        model.Add(room_vars[lab] == old_room_idx).OnlyEnforceIf(diff_room.Not())

        # lab changed if any field differs
        changed[lab] = model.NewBoolVar("changed_" + lab)
        model.AddMaxEquality(changed[lab], [diff_time, diff_day, diff_room])

        if lab == TOCHANGE:
            model.AddForbiddenAssignments([day_vars[lab], time_vars[lab]], [(5, 240)])

    # "at most one lab may differ"
    model.Add(sum(changed[lab] for lab in labs) <= 1)
