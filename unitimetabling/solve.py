from ortools.sat.python import cp_model

from model import (
    CLASS_DURATION,
    TOCHANGE,
    make_problem_data,
    build_model,
)


def solve_all(data):
    model, time_vars, day_vars, room_vars = build_model(data)

    class WorkshopMovements(cp_model.CpSolverSolutionCallback):
        def __init__(self, day_vars, time_vars, room_vars, lab_name, limit=None):
            super().__init__()
            self.day_vars = day_vars
            self.time_vars = time_vars
            self.room_vars = room_vars
            self.lab_name = lab_name
            self.limit = limit
            self.count = 0
            self.positions = set()  # (day, time, room_idx)

        def OnSolutionCallback(self):
            d = self.Value(self.day_vars[self.lab_name])
            t = self.Value(self.time_vars[self.lab_name])
            r_idx = self.Value(self.room_vars[self.lab_name])

            self.positions.add((d, t, r_idx))
            self.count += 1

            if self.limit is not None and self.count >= self.limit:
                self.StopSearch()

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False

    # TODO: change name
    callback = WorkshopMovements(day_vars, time_vars, room_vars, TOCHANGE, limit=None)
    solver.SearchForAllSolutions(model, callback)

    if not callback.positions:
        print("No feasible schedule / movement found for", TOCHANGE)
        return

    print("\nSuggested movements:")
    print(f"You can move '{TOCHANGE}' to these free timeslots "
          f"without interrupting any current assignments:\n")

    for (day, slot, room_idx) in sorted(callback.positions):
        start_total_minutes = 8 * 60 + slot
        start_hour = start_total_minutes // 60
        start_minute = start_total_minutes % 60

        end_total_minutes = start_total_minutes + CLASS_DURATION
        end_hour = end_total_minutes // 60
        end_minute = end_total_minutes % 60

        room_name = ["GPUA", "GPUB", "LINUX"][room_idx]
        print(
            f"- day {day}, "
            f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}, "
            f"room {room_name}"
        )


def solve(data):
    model, time_vars, day_vars, room_vars = build_model(data)
    labs = data["labs"]

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible schedule found")
        return

    print("\nOne feasible schedule:\n")

    for lab in labs:
        day = solver.Value(day_vars[lab])
        slot = solver.Value(time_vars[lab])
        room_idx = solver.Value(room_vars[lab])

        start_total_minutes = 8 * 60 + slot
        start_hour = start_total_minutes // 60
        start_minute = start_total_minutes % 60

        end_total_minutes = start_total_minutes + CLASS_DURATION
        end_hour = end_total_minutes // 60
        end_minute = end_total_minutes % 60

        room_name = ["GPUA", "GPUB", "LINUX"][room_idx]
        print(
            f"- {lab}: day {day}, "
            f"{slot}, "
            f"{start_hour:02d}:{start_minute:02d}-"
            f"{end_hour:02d}:{end_minute:02d}, "
            f"room {room_name}"
        )


if __name__ == "__main__":
    data = make_problem_data()
    solve_all(data)
