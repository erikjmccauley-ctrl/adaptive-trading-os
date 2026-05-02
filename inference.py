"""
Inference engine CLI — pools all backtest_*.csv files and prints the bucket analysis report.

Usage:
    python -X utf8 inference.py
"""
from src.inference import run_inference


def main():
    df = run_inference()
    df.to_csv('inference_results.csv', index=False)
    print(f'\n  Bucket results saved → inference_results.csv  ({len(df)} rows)')


if __name__ == '__main__':
    main()
