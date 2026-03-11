"""
Main Application Entry Point
"""
import os
import sys
import argparse
from typing import Dict, Any
import pandas as pd

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.agents.trading_agent import create_trading_agent, run_daily_analysis
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback to direct function calls
    from src.agents.trading_agent import run_daily_analysis
    create_trading_agent = None
from src.output.formatter import (
    format_as_markdown_table,
    format_as_json,
    format_as_detailed_report,
    format_recommendation
)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='A-Share Short-term Trading AI Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py                                    # Analyze all stocks, markdown output
  python src/main.py json                              # Analyze all stocks, JSON output
  python src/main.py --stocks 100                     # Analyze first 100 stocks
  python src/main.py --stocks 1000 detailed           # Analyze 1000 stocks, detailed report
  python src/main.py --stocks 500 recommendations     # Analyze 500 stocks, show recommendations only
        """
    )

    parser.add_argument(
        'format',
        nargs='?',
        choices=['markdown', 'json', 'detailed', 'recommendations'],
        default='markdown',
        help='Output format (default: markdown)'
    )

    parser.add_argument(
        '--stocks',
        type=int,
        default=0,
        help='Number of stocks to analyze (0 = all stocks, default: 0)'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )

    return parser.parse_args()

def main():
    """Main entry point for the A-Share trading agent"""
    args = parse_arguments()

    # Set environment variable for number of stocks to analyze
    if args.stocks > 0:
        os.environ['MAX_STOCKS_TO_ANALYZE'] = str(args.stocks)
        print(f"=== A-Share Short-term Trading AI Agent ===")
        print(f"正在分析前 {args.stocks} 只股票并生成交易建议...\n")
    else:
        print("=== A-Share Short-term Trading AI Agent ===")
        print("正在分析全部股票并生成交易建议...\n")

    # Run daily analysis
    try:
        results = run_daily_analysis()
        print(f"\n分析完成！日期: {results.get('date', '')}")
        print(f"分析股票数量: {results.get('total_analyzed', 0)}")
        print(f"推荐股票数量: {results.get('total_recommended', 0)}\n")

        # Display results in different formats
        if args.format == "json":
            print(format_as_json(results))
        elif args.format == "detailed":
            print(format_as_detailed_report(results))
        elif args.format == "recommendations":
            print("=== 交易建议详情 ===\n")
            for stock in results.get("recommended_stocks", []):
                recommendation = format_recommendation(stock)
                print(f"股票: {recommendation['名称']} ({recommendation['股票代码']})")
                print(f"买入区间: {recommendation['买入区间']}")
                print(f"目标价: {recommendation['目标价']}")
                print(f"防守价: {recommendation['防守价']}")
                print(f"持有期: {recommendation['持有期']}")
                print(f"推荐理由: {recommendation['推荐理由']}\n")
        else:
            print(format_as_markdown_table(results))

    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run_interactive_agent():
    """Run the interactive LangChain agent"""
    print("=== 交互式交易助手 ===")
    print("启动LangChain代理进行交互式分析...\n")

    try:
        agent_chain = create_trading_agent()

        # Example interaction
        result = agent_chain.invoke({
            "input": "请推荐3-5只适合明日交易的A股股票，并提供详细的交易建议。"
        })

        print("代理执行结果:")
        print(result)

    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    args = parse_arguments()
    if args.interactive:
        run_interactive_agent()
    else:
        main()