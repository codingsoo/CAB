import json
import pandas as pd
import os
import glob
from collections import Counter, defaultdict
import numpy as np

# Define model paths (both all-time and recent versions)
model_paths = {
    "ChatGPT 4.1 (all)": "CHANGE_IT_TO_YOUR_PATH", # Result directories
    "DeepSeek R1 (all)": "CHANGE_IT_TO_YOUR_PATH",
    "Llama 3.3 70B (all)": "CHANGE_IT_TO_YOUR_PATH",
    "Haiku 3.5 (all)": "CHANGE_IT_TO_YOUR_PATH",
    "Sonnet 3.7 (all)": "CHANGE_IT_TO_YOUR_PATH",
    "Sonnet 3.7 think (all)": "CHANGE_IT_TO_YOUR_PATH",
    "ChatGPT 4.1 (recent)": "CHANGE_IT_TO_YOUR_PATH",
    "DeepSeek R1 (recent)": "CHANGE_IT_TO_YOUR_PATH",
    "Llama 3.3 70B (recent)": "CHANGE_IT_TO_YOUR_PATH",
    "Haiku 3.5 (recent)": "CHANGE_IT_TO_YOUR_PATH",
    "Sonnet 3.7 (recent)": "CHANGE_IT_TO_YOUR_PATH",
    "Sonnet 3.7 think (recent)": "CHANGE_IT_TO_YOUR_PATH"
}

languages = ["c", "c#", "c++", "java", "javascript", "python", "typescript"]
target_verdicts = ["CORRECT", "PARTIALLY CORRECT", "INCORRECT"]

def read_jsonl(filepath):
    """Yield parsed JSON objects from a .jsonl file."""
    with open(filepath, 'r') as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def get_verdict_and_verbosity(entry):
    verdict = entry.get('final_verdict', entry.get('verdict', 'UNKNOWN'))
    verbosity = entry.get('final_alignment_score', {}).get('verbosity', 'UNKNOWN')
    return verdict, verbosity

def process_model(base_dir, model_name):
    total_entries = 0
    verdict_counts = Counter()
    verbose_counts = Counter()
    language_stats = {}
    language_verbose_stats = {}
    
    # Add new variables for tracking conversation lengths
    verdict_conv_lengths = defaultdict(list)
    verdict_history_lengths = defaultdict(list)
    language_conv_lengths = defaultdict(lambda: defaultdict(list))
    language_history_lengths = defaultdict(lambda: defaultdict(list))

    for language in languages:
        lang_dir = os.path.join(base_dir, language)
        if not os.path.exists(lang_dir):
            continue

        language_verdict_counts = Counter()
        language_verbose_counts = Counter()
        language_entries = 0

        for json_file in glob.glob(os.path.join(lang_dir, "*.jsonl")):
            for entry in read_jsonl(json_file):
                verdict, verbosity = get_verdict_and_verbosity(entry)
                if verdict not in target_verdicts:
                    continue

                # Get conversation lengths
                original_conv_length = (entry.get('original_conversation_length', 0) + 1) //2
                total_rounds = entry.get('total_conversation_rounds', 0)

                verdict_counts[verdict] += 1
                verbose_counts[verbosity] += 1
                language_verdict_counts[verdict] += 1
                language_verbose_counts[verbosity] += 1
                total_entries += 1
                language_entries += 1
                
                # Store conversation lengths
                verdict_conv_lengths[verdict].append(original_conv_length)
                verdict_history_lengths[verdict].append(total_rounds)
                language_conv_lengths[language][verdict].append(original_conv_length)
                language_history_lengths[language][verdict].append(total_rounds)

        language_stats[language] = {
            'total': language_entries,
            'verdicts': language_verdict_counts
        }
        language_verbose_stats[language] = language_verbose_counts

    # Calculate average conversation lengths
    avg_conv_lengths = {}
    avg_history_lengths = {}
    for verdict in target_verdicts:
        if verdict_counts[verdict] > 0:
            avg_conv_lengths[verdict] = sum(verdict_conv_lengths[verdict]) / len(verdict_conv_lengths[verdict])
            avg_history_lengths[verdict] = sum(verdict_history_lengths[verdict]) / len(verdict_history_lengths[verdict])

    return {
        'model_name': model_name,
        'total_entries': total_entries,
        'verdict_counts': verdict_counts,
        'verbose_counts': verbose_counts,
        'language_stats': language_stats,
        'language_verbose_stats': language_verbose_stats,
        'verdict_conv_lengths': dict(verdict_conv_lengths),
        'verdict_history_lengths': dict(verdict_history_lengths),
        'avg_conv_lengths': avg_conv_lengths,
        'avg_history_lengths': avg_history_lengths,
        'language_conv_lengths': dict(language_conv_lengths),
        'language_history_lengths': dict(language_history_lengths)
    }

def print_verdict_summary(model_results):
    print("\n=== OVERALL ACCURACY COMPARISON ACROSS MODELS ===")
    headers = [
        "Model", "Total", "CORRECT", "PART.CORR", "INCORRECT",
        "CORRECT%", "PART.CORR%", "INCORR%",
        "CORR-AvgConv", "PART-AvgConv", "INCORR-AvgConv",
        "CORR-LLMRound", "PART-LLMRound", "INCORR-LLMRound"  # 👈 added
    ]
    print(" | ".join(headers))
    print("-" * 180)

    for model_name, results in model_results.items():
        total = results['total_entries']
        correct = results['verdict_counts']['CORRECT']
        partially = results['verdict_counts']['PARTIALLY CORRECT']
        incorrect = results['verdict_counts']['INCORRECT']

        correct_pct = (correct / total) * 100 if total else 0
        partially_pct = (partially / total) * 100 if total else 0
        incorrect_pct = (incorrect / total) * 100 if total else 0

        # Average original conversation length
        correct_avg_conv = results['avg_conv_lengths'].get('CORRECT', 0)
        partially_avg_conv = results['avg_conv_lengths'].get('PARTIALLY CORRECT', 0)
        incorrect_avg_conv = results['avg_conv_lengths'].get('INCORRECT', 0)

        # 👇 Average LLM rounds
        correct_avg_llm = results['avg_history_lengths'].get('CORRECT', 0)
        partially_avg_llm = results['avg_history_lengths'].get('PARTIALLY CORRECT', 0)
        incorrect_avg_llm = results['avg_history_lengths'].get('INCORRECT', 0)

        row = [
            f"{model_name:<20}", f"{total:<5}", f"{correct:<7}", f"{partially:<9}", f"{incorrect:<9}",
            f"{correct_pct:6.2f}%", f"{partially_pct:9.2f}%", f"{incorrect_pct:7.2f}%",
            f"{correct_avg_conv:6.2f}", f"{partially_avg_conv:6.2f}", f"{incorrect_avg_conv:6.2f}",
            f"{correct_avg_llm:6.2f}", f"{partially_avg_llm:6.2f}", f"{incorrect_avg_llm:6.2f}"  # 👈 added
        ]
        print(" | ".join(row))


def print_verdict_summary(model_results):
    print("\n=== OVERALL ACCURACY COMPARISON ACROSS MODELS ===")
    headers = ["Model", "Total", "CORRECT", "PART.CORR", "INCORRECT", "CORRECT%", "PART.CORR%", "INCORR%", 
              "CORR-AvgConv", "PART-AvgConv", "INCORR-AvgConv"]
    print(" | ".join(headers))
    print("-" * 150)

    for model_name, results in model_results.items():
        total = results['total_entries']
        correct = results['verdict_counts']['CORRECT']
        partially = results['verdict_counts']['PARTIALLY CORRECT']
        incorrect = results['verdict_counts']['INCORRECT']
        correct_pct = (correct / total) * 100 if total else 0
        partially_pct = (partially / total) * 100 if total else 0
        incorrect_pct = (incorrect / total) * 100 if total else 0
        
        # Add average conversation lengths
        correct_avg_conv = results['avg_conv_lengths'].get('CORRECT', 0)
        partially_avg_conv = results['avg_conv_lengths'].get('PARTIALLY CORRECT', 0)
        incorrect_avg_conv = results['avg_conv_lengths'].get('INCORRECT', 0)

        row = [
            f"{model_name:<20}", f"{total:<5}", f"{correct:<7}", f"{partially:<9}", f"{incorrect:<9}",
            f"{correct_pct:6.2f}%", f"{partially_pct:9.2f}%", f"{incorrect_pct:7.2f}%",
            f"{correct_avg_conv:6.2f}", f"{partially_avg_conv:6.2f}", f"{incorrect_avg_conv:6.2f}"
        ]
        print(" | ".join(row))

def print_verbosity_summary(model_results):
    print("\n=== VERBOSITY ASSESSMENT COMPARISON ACROSS MODELS ===")
    headers = ["Model", "Total", "APPROPRIATE", "VERBOSE", "TERSE", "UNKNOWN", "APPR%", "VERB%", "TERSE%", "UNK%"]
    print(" | ".join(headers))
    print("-" * 120)

    for model_name, results in model_results.items():
        total = results['total_entries']
        counts = results['verbose_counts']
        appropriate = counts.get('APPROPRIATE', 0)
        verbose = counts.get('VERBOSE', 0)
        terse = counts.get('TERSE', 0)
        unknown = counts.get('UNKNOWN', 0)

        row = [
            f"{model_name:<20}", f"{total:<5}", f"{appropriate:<11}", f"{verbose:<7}",
            f"{terse:<5}", f"{unknown:<7}",
            f"{(appropriate / total * 100 if total else 0):5.2f}%",
            f"{(verbose / total * 100 if total else 0):5.2f}%",
            f"{(terse / total * 100 if total else 0):5.2f}%",
            f"{(unknown / total * 100 if total else 0):5.2f}%"
        ]
        print(" | ".join(row))

def print_per_language_stats(model_results):
    for language in languages:
        print(f"\n=== {language.upper()} LANGUAGE COMPARISON ACROSS MODELS ===")
        print("\nVERDICT COMPARISON:")
        headers = ["Model", "Total", "CORRECT", "PART.CORR", "INCORRECT", "CORRECT%", "PART.CORR%", "INCORR%",
                  "CORR-AvgConv", "PART-AvgConv", "INCORR-AvgConv"]
        print(" | ".join(headers))
        print("-" * 150)

        for model_name, results in model_results.items():
            stats = results['language_stats'].get(language, {'total': 0, 'verdicts': Counter()})
            total = stats['total']
            if total == 0:
                continue
            verdicts = stats['verdicts']
            correct = verdicts.get('CORRECT', 0)
            partially = verdicts.get('PARTIALLY CORRECT', 0)
            incorrect = verdicts.get('INCORRECT', 0)
            
            # Calculate average conversation lengths for this language and model
            lang_conv = results['language_conv_lengths'].get(language, {})
            correct_avg_conv = sum(lang_conv.get('CORRECT', [])) / len(lang_conv.get('CORRECT', [1])) if lang_conv.get('CORRECT', []) else 0
            partially_avg_conv = sum(lang_conv.get('PARTIALLY CORRECT', [])) / len(lang_conv.get('PARTIALLY CORRECT', [1])) if lang_conv.get('PARTIALLY CORRECT', []) else 0
            incorrect_avg_conv = sum(lang_conv.get('INCORRECT', [])) / len(lang_conv.get('INCORRECT', [1])) if lang_conv.get('INCORRECT', []) else 0

            row = [
                f"{model_name:<20}", f"{total:<5}", f"{correct:<7}", f"{partially:<9}",
                f"{incorrect:<9}", f"{(correct / total * 100):6.2f}%",
                f"{(partially / total * 100):9.2f}%", f"{(incorrect / total * 100):7.2f}%",
                f"{correct_avg_conv:6.2f}", f"{partially_avg_conv:6.2f}", f"{incorrect_avg_conv:6.2f}"
            ]
            print(" | ".join(row))

        print("\nVERBOSITY COMPARISON:")
        headers = ["Model", "Total", "APPROPRIATE", "VERBOSE", "TERSE", "UNKNOWN", "APPR%", "VERB%", "TERSE%", "UNK%"]
        print(" | ".join(headers))
        print("-" * 120)

        for model_name, results in model_results.items():
            total = results['language_stats'].get(language, {}).get('total', 0)
            if total == 0:
                continue
            verbose_stats = results['language_verbose_stats'].get(language, Counter())
            appropriate = verbose_stats.get('APPROPRIATE', 0)
            verbose = verbose_stats.get('VERBOSE', 0)
            terse = verbose_stats.get('TERSE', 0)
            unknown = verbose_stats.get('UNKNOWN', 0)

            row = [
                f"{model_name:<20}", f"{total:<5}", f"{appropriate:<11}", f"{verbose:<7}", f"{terse:<5}", f"{unknown:<7}",
                f"{(appropriate / total * 100):5.2f}%", f"{(verbose / total * 100):5.2f}%",
                f"{(terse / total * 100):5.2f}%", f"{(unknown / total * 100):5.2f}%"
            ]
            print(" | ".join(row))

def print_verdict_verbosity_relationship(model_results):
    print("\n=== VERDICT-VERBOSITY RELATIONSHIP ACROSS MODELS ===")

    for model_name, results in model_results.items():
        print(f"\n{model_name}:")
        print("  Verdict         | APPR%   VERB%   TERSE%  UNK%")
        print("  " + "-" * 45)

        verdict_verbose = {v: Counter() for v in target_verdicts}
        for language in languages:
            lang_dir = os.path.join(model_paths[model_name], language)
            if not os.path.exists(lang_dir):
                continue

            for json_file in glob.glob(os.path.join(lang_dir, "*.jsonl")):
                for entry in read_jsonl(json_file):
                    verdict, verbosity = get_verdict_and_verbosity(entry)
                    if verdict in target_verdicts:
                        verdict_verbose[verdict][verbosity] += 1

        for verdict in target_verdicts:
            dist = verdict_verbose[verdict]
            total = sum(dist.values())
            if total == 0:
                continue
            appr = dist.get('APPROPRIATE', 0) / total * 100
            verb = dist.get('VERBOSE', 0) / total * 100
            terse = dist.get('TERSE', 0) / total * 100
            unk = dist.get('UNKNOWN', 0) / total * 100

            print(f"  {verdict:<15} | {appr:6.2f}%  {verb:6.2f}%  {terse:6.2f}%  {unk:6.2f}%")

def print_conversation_stats(model_results):
    print("\n=== CONVERSATION LENGTH STATISTICS BY MODEL AND VERDICT ===")
    
    for model_name, results in model_results.items():
        print(f"\n{model_name}:")
        for verdict in target_verdicts:
            if verdict in results['verdict_conv_lengths'] and len(results['verdict_conv_lengths'][verdict]) > 0:
                conv_lengths = results['verdict_conv_lengths'][verdict]
                hist_lengths = results['verdict_history_lengths'][verdict]
                
                print(f"  {verdict}:")
                print(f"    Original Conversation Length - Min: {min(conv_lengths)}, Max: {max(conv_lengths)}, " 
                      f"Avg: {results['avg_conv_lengths'][verdict]:.2f}")
                print(f"    History Length - Min: {min(hist_lengths)}, Max: {max(hist_lengths)}, " 
                      f"Avg: {results['avg_history_lengths'][verdict]:.2f}")
                
                # Show distribution of conversation lengths
                conv_dist = Counter(conv_lengths)
                hist_dist = Counter(hist_lengths)
                
                print("    Original Conversation Length Distribution:")
                for length, count in sorted(conv_dist.items()):
                    percentage = (count / len(conv_lengths)) * 100
                    print(f"      Length {length}: {count} ({percentage:.2f}%)")
                
                print("    History Length Distribution:")
                for length, count in sorted(hist_dist.items()):
                    percentage = (count / len(hist_lengths)) * 100
                    print(f"      Length {length}: {count} ({percentage:.2f}%)")

# ==== Main Execution ====
model_results = {name: process_model(path, name) for name, path in model_paths.items()}

print_verdict_summary(model_results)
print_verbosity_summary(model_results)
print_per_language_stats(model_results)
print_verdict_verbosity_relationship(model_results)
print_conversation_stats(model_results)  # Added new function to print conversation stats