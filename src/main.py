"""Main entry point for GitHub AI Agent."""

import sys
import logging
import argparse
import time

from src.config import Configuration
from src.multi_repo_agent import MultiRepoAgent
from src.utils.errors import ConfigurationError


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='GitHub AI Agent - Autonomous developer agent for GitHub issues and PRs across multiple repositories'
    )
    parser.add_argument(
        '--config-file',
        type=str,
        help='Path to .env configuration file (default: .env in current directory)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--pr',
        action='store_true',
        help='Process only PRs with changes requested (skip issues)'
    )
    parser.add_argument(
        '--issue',
        action='store_true',
        help='Process only assigned issues (skip PRs)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Check interval in seconds (default: 300 = 5 minutes). Set to 0 for single run.'
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for GitHub AI Agent.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info("Loading configuration")
        config = Configuration.load(env_file=args.config_file)
        logger.info(f"Configuration loaded for organization: {config.github_organization}")
        logger.info(f"Repositories directory: {config.repositories_dir}")
        
        # Override processing modes based on command line arguments
        if args.pr and args.issue:
            # Both flags: process both (same as default)
            logger.info("Processing mode: Both issues and PRs")
            config.process_issues = True
            config.process_prs = True
        elif args.pr:
            # Only --pr flag: process PRs only
            logger.info("Processing mode: PRs only (--pr flag)")
            config.process_issues = False
            config.process_prs = True
        elif args.issue:
            # Only --issue flag: process issues only
            logger.info("Processing mode: Issues only (--issue flag)")
            config.process_issues = True
            config.process_prs = False
        else:
            # No flags: use config from .env (default: both)
            logger.info(f"Processing mode: Issues={config.process_issues}, PRs={config.process_prs}")
        
        # Check if running in loop mode or single run
        if args.interval == 0:
            # Single run mode
            logger.info("Starting GitHub AI Multi-Repo Agent (single run mode)")
            agent = MultiRepoAgent(config)
            exit_code = agent.run()
            
            if exit_code == 0:
                logger.info("Agent completed successfully")
            else:
                logger.error(f"Agent completed with errors (exit code: {exit_code})")
            
            return exit_code
        else:
            # Loop mode (continuous monitoring)
            logger.info(f"Starting GitHub AI Multi-Repo Agent (loop mode, check every {args.interval} seconds)")
            agent = MultiRepoAgent(config)
            
            run_count = 0
            while True:
                try:
                    run_count += 1
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"Run #{run_count} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"{'=' * 60}")
                    
                    exit_code = agent.run()
                    
                    if exit_code != 0:
                        logger.warning(f"Run #{run_count} completed with errors")
                    
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"Waiting {args.interval} seconds until next check...")
                    logger.info(f"Next check at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + args.interval))}")
                    logger.info(f"{'=' * 60}\n")
                    
                    time.sleep(args.interval)
                    
                except KeyboardInterrupt:
                    logger.info("\n\nAgent stopped by user (Ctrl+C)")
                    logger.info(f"Total runs completed: {run_count}")
                    return 0
                except Exception as e:
                    logger.error(f"Error in run #{run_count}: {e}", exc_info=True)
                    logger.info(f"Waiting {args.interval} seconds before retry...")
                    time.sleep(args.interval)
        
    except ConfigurationError as e:
        logger.critical(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("\nAgent stopped by user (Ctrl+C)")
        return 0
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
