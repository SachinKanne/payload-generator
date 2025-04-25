import json
import csv
import re

json_file_1 = "first.json"
json_file_2 = "second.json"
csv_output_file = "combined_perf_details.csv"

def parse_value_from_args(args_list, prefix):
    if not isinstance(args_list, list):
        return "NA"
    for arg in args_list:
        if isinstance(arg, str) and arg.startswith(prefix):
            try:
                return arg.split("=", 1)[1]
            except IndexError:
                return "NA"
    return "NA"

def parse_nebula_think_time(soleil_args_list):
    return parse_value_from_args(soleil_args_list, "thinkTimeMS=")

def calculate_total(avg_str, count_str):
    try:
        avg = float(avg_str)
        count = int(str(count_str).replace(',', ''))
        total = avg * count
        return str(int(round(total)))
    except (ValueError, TypeError, AttributeError):
        return "NA"

run_id = "N/A"
data1 = None
data2 = None

try:
    with open(json_file_1, 'r', encoding='utf-8') as f:
        data1 = json.load(f)
    if data1 and data1.get("perfruns") and data1["perfruns"]:
        run_id = data1["perfruns"][0].get("request_id", "N/A")
    else:
        print(f"Warning: Could not find RunId in {json_file_1}.")
except FileNotFoundError:
    print(f"Error: File not found - {json_file_1}. Cannot get RunId.")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from {json_file_1}: {e}. Cannot get RunId.")
except Exception as e:
    print(f"An unexpected error occurred reading {json_file_1}: {e}. Cannot get RunId.")

try:
    with open(json_file_2, 'r', encoding='utf-8') as f:
        data2 = json.load(f)
except FileNotFoundError:
    print(f"Error: File not found - {json_file_2}")
    data2 = None
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from {json_file_2}: {e}")
    data2 = None
except Exception as e:
    print(f"An unexpected error occurred reading {json_file_2}: {e}")
    data2 = None

template_details_header = [
    "RunId_Template",
    "Load Type",
    "Name",
    "Concurrent Users",
    "Think Time",
    "Load TPS",
]
template_rows = []

if data1:
    if data1.get("perfruns") and data1["perfruns"]:
        run_info = data1["perfruns"][0]
        payload = run_info.get("submitted_payload", {})
        workflow_spec = payload.get("workflow_spec", {})
        templates = workflow_spec.get("on_the_fly_templates", [])

        if not templates:
            print(f"Warning: No 'on_the_fly_templates' found in {json_file_1}.")
        else:
            for template in templates:
                load_type = template.get("load_type", "N/A")
                name = template.get("name", "N/A")
                execution = template.get("execution", {})
                args = execution.get("args", [])
                config = execution.get("config", {})

                concurrent_users = "NA"
                think_time = "NA"
                load_tps = "NA"

                if load_type == "nebula":
                    concurrent_users = config.get("number_users", "NA")
                    usecases = config.get("usecases", [])
                    if usecases and isinstance(usecases, list) and len(usecases) > 0:
                         soleil_args = usecases[0].get("soleil_args", [])
                         think_time = parse_nebula_think_time(soleil_args)

                elif load_type == "jmeter":
                    users1 = parse_value_from_args(args, "-Jusers=")
                    users2 = parse_value_from_args(args, "-Jnum_threads=")
                    concurrent_users = users1 if users1 != "NA" else users2
                    think_time = parse_value_from_args(args, "-Jthink_time_in_ms=")
                    load_tps = parse_value_from_args(args, "-Jthroughput_per_sec=")

                elif load_type == "k6":
                    concurrent_users = parse_value_from_args(args, "-eNO_VU=")
                    load_tps = parse_value_from_args(args, "-eRATE_PER_TIME_UNIT=")

                elif load_type == "replayforce":
                     rate_count_str = parse_value_from_args(args, "--replayforce.replay.fixedRate.count=")
                     rate_interval_str = parse_value_from_args(args, "--replayforce.replay.fixedRate.intervalInSec=")
                     try:
                         count = float(rate_count_str)
                         interval = float(rate_interval_str)
                         if interval != 0:
                             tps_calc = count / interval
                             load_tps = int(tps_calc) if tps_calc.is_integer() else tps_calc
                             load_tps = str(load_tps)
                         else: load_tps = "NA"
                     except (ValueError, TypeError): load_tps = "NA"

                template_rows.append([
                    run_id, load_type, name, concurrent_users, think_time, load_tps,
                ])
    else:
        print(f"Warning: 'perfruns' key not found or empty in {json_file_1}.")

log_summary_header = [
    "RunId_Log",
    "Type",
    "Log Record Type",
    "Count",
    "Avg CPU Time",
    "Total App CPU (ms)",
    "Avg RunTime",
    "Total runTime (ms)",
    "Avg DBTotalTime (ms)",
    "Total DBTime (ms)",
    "Avg Allocated Memory (MB)",
    "Total Allocated Memory (MB)",
]
log_summary_rows = []

if data2:
    perf_run_results = data2.get("PerfRunResults", {})
    splunk_results = perf_run_results.get("SPLUNK", [])
    detailed_metrics_results = None
    summary_metrics_results = None

    for metric_result in splunk_results:
        metric_name = metric_result.get("name")
        if metric_name == "Core Cost Logline Detailed Metrics":
            detailed_metrics_results = metric_result.get("runresult", {}).get("results", [])
        elif metric_name == "Summary Core Cost Logline Metrics":
            summary_metrics_results = metric_result.get("runresult", {}).get("results", [])

    if detailed_metrics_results:
        for item in detailed_metrics_results:
            if not isinstance(item, dict): continue
            log_type = item.get("LogRecordType", "N/A")
            count = item.get("Request Count", "0")
            avg_cpu = item.get("Avg CpuTime (ms)", "N/A")
            avg_runtime = item.get("Avg RunTime (ms)", "N/A")
            avg_dbtime = item.get("Avg DBTotalTime (ms)", "N/A")
            avg_mem = item.get("Avg Allocated Memory (MB)", "N/A")
            total_cpu = calculate_total(avg_cpu, count)
            total_runtime = calculate_total(avg_runtime, count)
            total_dbtime = calculate_total(avg_dbtime, count)
            total_mem = calculate_total(avg_mem, count)
            display_count = str(count)
            log_summary_rows.append([
                run_id, "Individual", log_type, display_count, avg_cpu, total_cpu,
                avg_runtime, total_runtime, avg_dbtime, total_dbtime, avg_mem, total_mem,
            ])
    else:
        print("Warning: 'Core Cost Logline Detailed Metrics' not found in second.json.")

    if summary_metrics_results and len(summary_metrics_results) > 0:
        item = summary_metrics_results[0]
        if isinstance(item, dict):
            log_type = "ALL Logs"
            count = item.get("Request Count", "0")
            avg_cpu = item.get("Avg CpuTime (ms)", "N/A")
            avg_runtime = item.get("Avg RunTime (ms)", "N/A")
            avg_dbtime = item.get("Avg DBTotalTime (ms)", "N/A")
            avg_mem = item.get("Avg Allocated Memory (MB)", "N/A")
            total_cpu = calculate_total(avg_cpu, count)
            total_runtime = calculate_total(avg_runtime, count)
            total_dbtime = calculate_total(avg_dbtime, count)
            total_mem = calculate_total(avg_mem, count)
            display_count = str(count)
            log_summary_rows.append([
                run_id, "Aggregate", log_type, display_count, avg_cpu, total_cpu,
                avg_runtime, total_runtime, avg_dbtime, total_dbtime, avg_mem, total_mem,
            ])
    else:
        print("Warning: 'Summary Core Cost Logline Metrics' not found or empty in second.json.")

    log_summary_rows.sort(key=lambda row: (row[1] != 'Aggregate', row[2]))
else:
    print(f"No data loaded from {json_file_2}. Cannot generate log summary details.")

combined_header = template_details_header + log_summary_header
combined_rows = []

num_template_rows = len(template_rows)
num_log_rows = len(log_summary_rows)
max_rows = max(num_template_rows, num_log_rows)

blank_template_row = [""] * len(template_details_header)
blank_log_row = [""] * len(log_summary_header)

for i in range(max_rows):
    row1_data = template_rows[i] if i < num_template_rows else blank_template_row
    row2_data = log_summary_rows[i] if i < num_log_rows else blank_log_row
    combined_rows.append(row1_data + row2_data)

if combined_rows:
    try:
        with open(csv_output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(combined_header)
            writer.writerows(combined_rows)
        print(f"Successfully created combined file: {csv_output_file}")
        if num_template_rows != num_log_rows:
            print(f"Note: Datasets had different row counts ({num_template_rows} vs {num_log_rows}). Shorter dataset padded with blanks.")
    except IOError as e:
        print(f"Error writing {csv_output_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while writing {csv_output_file}: {e}")
else:
    print(f"No data extracted to write to {csv_output_file}.")
