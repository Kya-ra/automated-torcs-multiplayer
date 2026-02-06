import pandas as pd
import os
import xml.etree.ElementTree as et

log_filepath = "logs/racelog.csv"
results_filepath = "../torcs/results/quickrace/"

def add_car_stats(BASE_SPEED, MIN_SPEED, MAX_SPEED, K_CURVE, STEER_GAIN, CENTER_GAIN, STEER_SMOOTH_ALPHA, BRAKE_ANGLE_TH, BRAKE_MAX, ENABLE_TC, TC_SLIP_TH, TC_ACCEL_CUT):

    if not os.path.exists(log_filepath):
        df = pd.DataFrame(columns=["base_speed", "min_speed", "max_speed", "k_curve", "steer_gain", "center_gain", "steer_smooth_alpha", "brake_angle_th", "brake_max", "enable_tc", "tc_slip_th", "tc_accel_cut", "driver_name", "car", "top_speed", "lap_amount","best_lap_time (seconds)", "full_time (seconds)"])
        df.to_csv(log_filepath, index=False)

    df = pd.read_csv(log_filepath)

    new_data = {
        "base_speed": BASE_SPEED,
        "min_speed": MIN_SPEED,
        "max_speed": MAX_SPEED,
        "k_curve": K_CURVE,
        "steer_gain": STEER_GAIN,
        "center_gain": CENTER_GAIN,
        "steer_smooth_alpha": STEER_SMOOTH_ALPHA,
        "brake_angle_th": BRAKE_ANGLE_TH,
        "brake_max": BRAKE_MAX,
        "enable_tc": ENABLE_TC,
        "tc_slip_th": TC_SLIP_TH,
        "tc_accel_cut": TC_ACCEL_CUT,

        "driver_name": "",
        "car": "",
        "top_speed": None,
        "lap_amount": None,
        "best_lap_time (seconds)": None,
        "full_time (seconds)": None,
    }

    df.loc[len(df)] = new_data

    df.to_csv(log_filepath, index=False)

def add_race_stats():
    df = pd.read_csv(log_filepath)

    for col in ["driver_name", "car"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype("string")

    if df.empty:
        raise RuntimeError("racelog.csv has no rows. Call add_car_stats() before add_race_stats().")

    xml_files = [
        os.path.join(results_filepath, f)
        for f in os.listdir(results_filepath)
        if f.lower().endswith(".xml")
    ]

    if not xml_files:
        raise FileNotFoundError(f"No .xml files found in: {results_filepath}")

    newest_stat = max(xml_files, key=os.path.getmtime)

    tree = et.parse(newest_stat)
    root = tree.getroot()

    rank1 = root.find(".//section[@name='Rank']/section[@name='1']")
    if rank1 is None:
        raise RuntimeError("Could not find Rank/1 section in the newest results XML.")

    xml_data = {}
    for elem in rank1:
        key = elem.attrib.get("name")
        val = elem.attrib.get("val")
        if key is not None:
            xml_data[key] = val

    def to_float(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    last_row_index = len(df) - 1

    df.loc[last_row_index, "driver_name"] = xml_data.get("name", "")
    df.loc[last_row_index, "car"] = xml_data.get("car", "")
    df.loc[last_row_index, "top_speed"] = to_float(xml_data.get("top speed"))
    df.loc[last_row_index, "lap_amount"] = to_float(xml_data.get("laps"))
    df.loc[last_row_index, "best_lap_time (seconds)"] = to_float(xml_data.get("best lap time"))
    df.loc[last_row_index, "full_time (seconds)"] = to_float(xml_data.get("time"))

    df.to_csv(log_filepath, index=False)

def check_for_new_file(file_amount):

    while True:
        xml_files_new = [
            os.path.join(results_filepath, f)
            for f in os.listdir(results_filepath)
            if f.lower().endswith(".xml")
        ]

        if file_amount < len(xml_files_new):
            break




if __name__ == "__main__":
    
    #add_race_stats()
    print("This file should not be run by itself, the torcs_jm_par.py file for the car bot will automatically run this")