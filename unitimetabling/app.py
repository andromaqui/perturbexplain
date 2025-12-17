from model_data import make_problem_data
from model import build_model
from solve import solve_show_all


if __name__ == "__main__":
    data = make_problem_data()
    model, starttime_vars, day_vars, room_vars = build_model(data)
    solve_show_all(data, model, starttime_vars, day_vars, room_vars)
