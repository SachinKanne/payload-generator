import json
import re

json_file_1 = "first.json"
json_file_2 = "second.json"
json_output_file = "combined_perf_details.json"

def parse_value_from_args(args_list, prefix):
    if not isinstance(args_list, list): return "NA"
    for arg in args_list:
        if isinstance(arg, str) and arg.startswith(prefix):
            try:
                return arg.split("=", 1)[1]
            except IndexError: return "NA"
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
root_key = "Unknown Performance Test Run"

try:
    with open(json_file_1, 'r', encoding='utf-8') as f:
        data1 = json.load(f)
    if data1 and data1.get("perfruns") and data1["perfruns"]:
        run_id = data1["perfruns"][0].get("request_id", "N/A")
        if run_id != "N/A":
             root_key = f"Performance Test Run ({run_id})"
    else:
        print(f"Warning: Could not find RunId in {json_file_1}.")
except FileNotFoundError: print(f"Error: File not found - {json_file_1}.")
except json.JSONDecodeError as e: print(f"Error decoding JSON from {json_file_1}: {e}.")
except Exception as e: print(f"An unexpected error occurred reading {json_file_1}: {e}.")

try:
    with open(json_file_2, 'r', encoding='utf-8') as f:
        data2 = json.load(f)
except FileNotFoundError: print(f"Error: File not found - {json_file_2}")
except json.JSONDecodeError as e: print(f"Error decoding JSON from {json_file_2}: {e}")
except Exception as e: print(f"An unexpected error occurred reading {json_file_2}: {e}")

output_data = {
    root_key: {
        "input_payload": {
            "loads": []
        },
        "output_metrics": {
            "aggregated_metrics": {},
            "individual_metrics": []
        }
    }
}

if data1:
    if data1.get("perfruns") and data1["perfruns"]:
        run_info = data1["perfruns"][0]
        payload = run_info.get("submitted_payload", {})
        workflow_spec = payload.get("workflow_spec", {})
        templates = workflow_spec.get("on_the_fly_templates", [])

        if not templates:
            print(f"Warning: No 'on_the_fly_templates' found in {json_file_1} to populate input_payload.")
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
                    concurrent_users = str(config.get("number_users", "NA"))
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
                             load_tps = str(int(tps_calc) if tps_calc.is_integer() else tps_calc)
                         else: load_tps = "NA"
                     except (ValueError, TypeError): load_tps = "NA"

                load_details = {
                    "load_name": name,
                    "load_type": load_type,
                    "concurrent_users": concurrent_users,
                    "think_time": think_time,
                    "load_tps": load_tps
                }
                output_data[root_key]["input_payload"]["loads"].append(load_details)

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

    if summary_metrics_results and len(summary_metrics_results) > 0:
        item = summary_metrics_results[0]
        if isinstance(item, dict):
            count = item.get("Request Count", "0")
            avg_cpu = item.get("Avg CpuTime (ms)", "N/A")
            avg_runtime = item.get("Avg RunTime (ms)", "N/A")
            avg_dbtime = item.get("Avg DBTotalTime (ms)", "N/A")
            avg_mem = item.get("Avg Allocated Memory (MB)", "N/A")

            aggregate_metrics_dict = {
                "log_record_type": "ALL Logs",
                "count": str(count),
                "avg_cpu_time": avg_cpu,
                "total_app_cpu": calculate_total(avg_cpu, count),
                "avg_runtime": avg_runtime,
                "total_runtime": calculate_total(avg_runtime, count),
                "avg_db_total_time": avg_dbtime,
                "total_db_time": calculate_total(avg_dbtime, count),
                "avg_allocated_memory_mb": avg_mem,
                "total_allocated_memory_mb": calculate_total(avg_mem, count)
            }
            output_data[root_key]["output_metrics"]["aggregated_metrics"] = aggregate_metrics_dict
        else:
             print("Warning: 'Summary Core Cost Logline Metrics' result item is not a dictionary.")
    else:
        print("Warning: 'Summary Core Cost Logline Metrics' not found or empty in second.json.")

    if detailed_metrics_results:
        detailed_metrics_results.sort(key=lambda x: x.get("LogRecordType", "") if isinstance(x, dict) else "")

        for item in detailed_metrics_results:
            if not isinstance(item, dict): continue

            log_type = item.get("LogRecordType", "N/A")
            count = item.get("Request Count", "0")
            avg_cpu = item.get("Avg CpuTime (ms)", "N/A")
            avg_runtime = item.get("Avg RunTime (ms)", "N/A")
            avg_dbtime = item.get("Avg DBTotalTime (ms)", "N/A")
            avg_mem = item.get("Avg Allocated Memory (MB)", "N/A")

            individual_metric_set = {
                 "log_record_type": log_type,
                 "count": str(count),
                 "avg_cpu_time": avg_cpu,
                 "total_app_cpu": calculate_total(avg_cpu, count),
                 "avg_runtime": avg_runtime,
                 "total_runtime": calculate_total(avg_runtime, count),
                 "avg_db_total_time": avg_dbtime,
                 "total_db_time": calculate_total(avg_dbtime, count),
                 "avg_allocated_memory_mb": avg_mem,
                 "total_allocated_memory_mb": calculate_total(avg_mem, count)
            }
            output_data[root_key]["output_metrics"]["individual_metrics"].append(individual_metric_set)
    else:
        print("Warning: 'Core Cost Logline Detailed Metrics' not found in second.json.")
else:
     print(f"Warning: No data loaded from {json_file_2}. Cannot populate output_metrics.")

try:
    with open(json_output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)
    print(f"Successfully created combined JSON file: {json_output_file}")
except IOError as e:
    print(f"Error writing {json_output_file}: {e}")
except Exception as e:
    print(f"An unexpected error occurred while writing {json_output_file}: {e}")
