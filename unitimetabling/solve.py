from ortools.sat.python import cp_model
from itertools import combinations


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


class Movements(cp_model.CpSolverSolutionCallback):
    def __init__(self, day_vars, time_vars, room_vars, lab_name, limit=None):
        super().__init__()
        self.day_vars = day_vars
        self.time_vars = time_vars
        self.room_vars = room_vars
        self.lab_name = lab_name
        self.limit = limit
        self.count = 0
        self.positions = set()

    def OnSolutionCallback(self):
        d = self.Value(self.day_vars[self.lab_name])
        t = self.Value(self.time_vars[self.lab_name])
        r_idx = self.Value(self.room_vars[self.lab_name])

        self.positions.add((d, t, r_idx))
        self.count += 1

        if self.limit is not None and self.count >= self.limit:
            self.StopSearch()


class AllSchedules(cp_model.CpSolverSolutionCallback):
    def __init__(self, day_vars, time_vars, room_vars, labs, limit_unique=None):
        super().__init__()
        self.day_vars = day_vars
        self.time_vars = time_vars
        self.room_vars = room_vars
        self.labs = list(labs)
        self.raw_count = 0
        self.seen = set()
        self.unique = []
        self.limit_unique = limit_unique

    def OnSolutionCallback(self):
        self.raw_count += 1

        schedule = {
            lab: (
                self.Value(self.day_vars[lab]),
                self.Value(self.time_vars[lab]),
                self.Value(self.room_vars[lab]),
            )
            for lab in self.labs
        }

        key = tuple((lab, *schedule[lab]) for lab in self.labs)

        if key in self.seen:
            return

        self.seen.add(key)
        self.unique.append(schedule)

        if self.limit_unique is not None and len(self.unique) >= self.limit_unique:
            self.StopSearch()


def solve_show_all(data, model, starttime_vars, day_vars, room_vars):
    labs = data["labs"]
    lab_duration = data["CLASS_DURATION"]
    to_change = data["TO_CHANGE"]
    num_perturbations  = data["NUM_PERTURBATIONS"]

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False

    callback = AllSchedules(day_vars, starttime_vars, room_vars, labs, limit_unique=None)
    solver.SearchForAllSolutions(model, callback)

    if callback.raw_count == 0:
        print("No feasible schedule found.")
        return

    print("Raw solver solutions visited:", callback.raw_count)
    print("Unique schedules (by day/time/room):", len(callback.unique))

    if num_perturbations is not None:
        print("\nFeasible schedules with perturbations:\n")

        for i, schedule in enumerate(callback.unique, 1):
            print(f"Solution {i}:")
            for lab in labs:
                day, slot, room_idx = schedule[lab]

                start = 8 * 60 + slot
                end = start + lab_duration[lab]
                room_name = ["GPUA", "GPUB", "LINUX"][room_idx]

                print(
                    f"  - {lab}: day {day}, "
                    f"slot: {slot}, "
                    f"{start // 60:02d}:{start % 60:02d}-"
                    f"{end // 60:02d}:{end % 60:02d}, "
                    f"room {room_name}"
                )
            print()
    else:
        callback = Movements(day_vars, starttime_vars, room_vars, to_change)
        solver.SearchForAllSolutions(model, callback)

        if not callback.positions:
            print("No feasible schedule / movement found for", to_change)
            return
        else:
            print("You can schedule " + to_change + " on the following times:")
            print("")

            for row in callback.positions:
                day = row[0]
                slot = row[1]
                room_idx = row[2]

                start = 8 * 60 + slot
                end = start + lab_duration
                room_name = ["GPUA", "GPUB", "LINUX"][room_idx]

                print(f"day: {day}, "
                      f"slot: {slot}, "
                      f"start_time: {start // 60:02d}:{start % 60:02d} "
                      f"end_time: {end // 60:02d}:{end % 60:02d} "
                      f"room: {room_name}"
                      )


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
