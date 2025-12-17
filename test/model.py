from ortools.sat.python import cp_model
from itertools import combinations
from model_data import make_problem_data

# 7 days
# labs start from 8AM to 5PM
# labs last only 1 hour
# there is an old schedule and you should try to change a given time
# 0, 60, 120, 180, 240
# TODO: preferences
# TODO: TESTS
# TODO: demonstrators
# TODO: room distance


# TODO: objective function
# preferences of dozierenden
# preferences of demonstrators ??
# maximize the time a lecturers spends in uni in 1 day(
# maximize the time a student spends in uni in 1 day
# use resources in the most optimal way ???
# maximize the amount of labs which are assigned? can some be unassigned?

# plot tests on small dataset
# plot test on big dataset



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
#NUM_PERTURBATIONS = None


def build_model(data, max_perturbations=None):
    model = cp_model.CpModel()

    NUM_TIME_SLOTS = data["NUM_TIME_SLOTS"]
    NUM_DAYS = data["NUM_DAYS"]
    NUM_ROOMS = data["NUM_ROOMS"]

    lab_duration = data["lab_duration"]
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

    starttime_vars = {}
    day_vars = {}
    slot_vars = {}
    room_vars = {}
    is_on_GPUA = {}
    is_on_GPUB = {}

    linux_vars = []

    for lab in labs:
        startminute_var = model.NewIntVar(0, NUM_TIME_SLOTS - lab_duration[lab], "time_" + lab)
        starttime_vars[lab] = startminute_var

        # Restrict to 15-minute intervals: 0, 15, 30, 45, 60, 75, 90, ...
        # (8:00, 8:15, 8:30, 8:45, 9:00, 9:15, 9:30, ...)
        allowed_starts = list(range(0, NUM_TIME_SLOTS - lab_duration[lab] + 1, 15))
        model.AddAllowedAssignments([startminute_var], [(s,) for s in allowed_starts])

        day_vars[lab] = model.NewIntVar(0, len(day_slots) - 1, "day_" + lab)
        slot_vars[lab] = model.NewIntVar(0, NUM_DAYS * SLOTS_PER_DAY - 1, f"slot_{lab}")
        model.Add(slot_vars[lab] == day_vars[lab] * SLOTS_PER_DAY + starttime_vars[lab])

        model.Add(starttime_vars[lab] != 4 * 60)

        if lab in lab_day:
            model.AddAllowedAssignments([day_vars[lab]], [(d,) for d in lab_day[lab]])

        lec = lab_lecturer[lab]
        if lec in lecturer_forbidden:
            for day, slot in lecturer_forbidden[lec]:
                if slot == -1:
                    for s in range(SLOTS_PER_DAY):
                        model.Add(day_vars[lab] != day)
                else:
                    model.AddForbiddenAssignments([day_vars[lab], starttime_vars[lab]], [(day, slot)])

        if lab in rooms_to_classes["GPUA"] or lab in rooms_to_classes["GPUB"]:
            room_vars[lab] = model.NewIntVar(0, len(room_slots) - 2, "room_" + lab)

            is_on_GPUA[lab] = model.NewBoolVar("is_on_GPUA_" + lab)
            is_on_GPUB[lab] = model.NewBoolVar("is_on_GPUB_" + lab)

            model.Add(room_vars[lab] == GPUA).OnlyEnforceIf(is_on_GPUA[lab])
            model.Add(room_vars[lab] == GPUB).OnlyEnforceIf(is_on_GPUB[lab])
            model.Add(is_on_GPUA[lab] + is_on_GPUB[lab] == 1)
        else:
            room_vars[lab] = model.NewIntVar(LINUX, LINUX, "room_" + lab)
            linux_vars.append(starttime_vars[lab])

        apply_old_plan_constraints(
            model,
            lab,
            starttime_vars,
            day_vars,
            room_vars,
            OLDPLAN,
            TOCHANGE
        )

    '''
        if max_perturbations is not None:
            apply_old_plan_constraints_up_to_n_changes(
                model,
                labs,
                time_vars,
                day_vars,
                room_vars,
                OLDPLAN,
                TOCHANGE,
                max_perturbations
            )
    '''

    # 1 hour after the other
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            lab_i = labs[i]
            lab_j = labs[j]

            same = model.NewBoolVar("same_room_" + lab_i + "_" + lab_j)
            model.Add(room_vars[lab_i] == room_vars[lab_j]).OnlyEnforceIf(same)
            model.Add(room_vars[lab_i] != room_vars[lab_j]).OnlyEnforceIf(same.Not())

            before = model.NewBoolVar("before_" + lab_i + "_" + lab_j)
            model.Add(starttime_vars[lab_i] + lab_duration[lab_i] <= starttime_vars[lab_j]).OnlyEnforceIf([same, before])
            model.Add(starttime_vars[lab_j] + lab_duration[lab_j] <= starttime_vars[lab_i]).OnlyEnforceIf([same, before.Not()])

    labStudentIntersections = find_lab_studentintersections(data)

    for lab in labStudentIntersections:
        for other_lab in labStudentIntersections[lab]:
            if lab >= other_lab:
                continue

            b = model.NewBoolVar(f"no_overlap_{lab}_{other_lab}")
            model.Add(slot_vars[lab] + lab_duration[lab] <= slot_vars[other_lab]).OnlyEnforceIf(b)
            model.Add(slot_vars[other_lab] + lab_duration[other_lab]<= slot_vars[lab]).OnlyEnforceIf(b.Not())

    return model, starttime_vars, day_vars, room_vars


def find_lab_studentintersections(data):
    lab_to_studentIds = data["lab_to_studentIds"]
    lab_sets = {lab: set(ids) for lab, ids in lab_to_studentIds.items()}
    conflicts = {lab: [] for lab in lab_sets}

    for lab1, lab2 in combinations(lab_sets.keys(), 2):
        if lab_sets[lab1] & lab_sets[lab2]:
            conflicts[lab1].append(lab2)
            conflicts[lab2].append(lab1)

    return conflicts


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


def apply_old_plan_constraints_up_to_n_changes(
        model,
        labs,
        time_vars,
        day_vars,
        room_vars,
        OLDPLAN,
        TOCHANGE,
        max_perturbations
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
    model.Add(sum(changed[lab] for lab in labs) <= max_perturbations + 1)


def solve_show_all(data):
    model, time_vars, day_vars, room_vars = build_model(data, None)

    # TODO:
    class Movements(cp_model.CpSolverSolutionCallback):
        def __init__(self, day_vars, time_vars, room_vars, lab_name, limit=None):
            super().__init__()
            self.day_vars = day_vars
            self.time_vars = time_vars
            self.room_vars = room_vars
            self.lab_name = lab_name
            self.limit = limit
            self.count = 0
            # TODO: what is happening here?
            self.positions = set()

        def OnSolutionCallback(self):
            d = self.Value(self.day_vars[self.lab_name])
            t = self.Value(self.time_vars[self.lab_name])
            r_idx = self.Value(self.room_vars[self.lab_name])

            self.positions.add((d, t, r_idx, self.lab_name))
            self.count += 1

            if self.limit is not None and self.count >= self.limit:
                self.StopSearch()

    solver = cp_model.CpSolver()
    callback = Movements(day_vars, time_vars, room_vars, TOCHANGE)
    solver.SearchForAllSolutions(model, callback)

    if not callback.positions:
        print("No feasible schedule / movement found for", TOCHANGE)
        return
    else:
        # TODO: fstrings
        print("You can schedule " +  TOCHANGE + " on the following times:")
        print("")

        for row in callback.positions:
            day = row[0]
            slot = row[1]
            room_idx = row[2]

            start = 8 * 60 + slot
            end = start + CLASS_DURATION
            room_name = ["GPUA", "GPUB", "LINUX"][room_idx]

            print(f"day: {day}, "
                  f"slot: {slot}, "
                  f"start_time: {start // 60:02d}:{start % 60:02d} "
                  f"room: {room_name}"
                  )

if __name__ == "__main__":
    data = make_problem_data()
    solve_show_all(data)
