def make_problem_data():
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
    NUM_PERTURBATIONS = 1


    lab_duration = {
        "machinelearning": 60,
        "computervision": 90,
        "cloudcomputing": 120,
        "workshopinai": 60
    }

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
        "CLASS_DURATION": lab_duration,
        "TO_CHANGE": TOCHANGE,
        "OLD_PLAN": OLDPLAN,
        "NUM_PERTURBATIONS": NUM_PERTURBATIONS,
        "NUM_TIME_SLOTS": NUM_TIME_SLOTS,
        "NUM_DAYS": NUM_DAYS,
        "NUM_ROOMS": NUM_ROOMS,
        "lab_duration": lab_duration,
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

