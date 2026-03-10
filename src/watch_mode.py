"""Watch mode for continuous monitoring of issues and PRs."""

import logging
import time
from datetime import datetime
from typing import Set

from src.config import Configuration
from src.multi_repo_agent import MultiRepoAgent


logger = logging.getLogger(__name__)


class WatchMode:
    """Watch mode for continuous monitoring and automatic processing."""
    
    def __init__(self, config: Configuration, check_interval: int = 300):
        """Initialize watch mode.
        
        Args:
            config: Agent configuration
            check_interval: Interval between checks in seconds (default: 300 = 5 minutes)
        """
        self.config = config
        self.check_interval = check_interval
        self.agent = MultiRepoAgent(config)
        self.processed_items: Set[str] = set()  # Track processed items to avoid duplicates
        
        logger.info(f"Watch mode initialized with check interval: {check_interval} seconds")
    
    def run(self) -> None:
        """Run agent in watch mode (continuous monitoring).
        
        This will:
        1. Check for new issues and PRs every {check_interval} seconds
        2. Process new items automatically
        3. Keep running until interrupted (Ctrl+C)
        """
        logger.info("=" * 60)
        logger.info("GitHub AI Agent - WATCH MODE")
        logger.info(f"Organization: {self.config.github_organization}")
        logger.info(f"Check interval: {self.check_interval} seconds ({self.check_interval // 60} minutes)")
        logger.info("=" * 60)
        logger.info("\n🔄 Agent is now in STANDBY mode...")
        logger.info("Monitoring for new issues and PRs...")
        logger.info("Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                logger.info("=" * 60)
                logger.info(f"Check #{iteration} - {current_time}")
                logger.info("=" * 60)
                
                try:
                    # Run agent to check for new work
                    logger.info("Checking for new issues and PRs...")
                    exit_code = self.agent.run()
                    
                    if exit_code == 0:
                        logger.info("✓ Check completed successfully")
                    else:
                        logger.warning(f"⚠ Check completed with errors (exit code: {exit_code})")
                    
                except Exception as e:
                    logger.error(f"Error during check: {e}", exc_info=True)
                
                # Wait before next check
                next_check = datetime.now()
                next_check = next_check.replace(
                    second=0, 
                    microsecond=0
                )
                # Add check_interval seconds
                import datetime as dt
                next_check = next_check + dt.timedelta(seconds=self.check_interval)
                next_check_str = next_check.strftime("%H:%M:%S")
                
                logger.info(f"\n💤 Standby... Next check at {next_check_str}")
                logger.info(f"   (Waiting {self.check_interval} seconds / {self.check_interval // 60} minutes)")
                logger.info("-" * 60 + "\n")
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("🛑 Watch mode stopped by user (Ctrl+C)")
            logger.info(f"Total checks performed: {iteration}")
            logger.info("=" * 60)
    
    def run_once_then_watch(self) -> None:
        """Run agent once immediately, then enter watch mode.
        
        This is useful for:
        1. Process any existing issues/PRs immediately
        2. Then monitor for new ones
        """
        logger.info("=" * 60)
        logger.info("GitHub AI Agent - INITIAL RUN + WATCH MODE")
        logger.info("=" * 60)
        
        # Initial run
        logger.info("\n🚀 Running initial check...")
        try:
            exit_code = self.agent.run()
            if exit_code == 0:
                logger.info("✓ Initial check completed successfully")
            else:
                logger.warning(f"⚠ Initial check completed with errors")
        except Exception as e:
            logger.error(f"Error during initial check: {e}", exc_info=True)
        
        # Enter watch mode
        logger.info("\n🔄 Entering watch mode...")
        time.sleep(2)  # Brief pause
        self.run()


class SmartWatchMode(WatchMode):
    """Smart watch mode with adaptive check intervals."""
    
    def __init__(
        self, 
        config: Configuration, 
        min_interval: int = 300,
        max_interval: int = 1800,
        idle_threshold: int = 3
    ):
        """Initialize smart watch mode.
        
        Args:
            config: Agent configuration
            min_interval: Minimum check interval in seconds (default: 300 = 5 minutes)
            max_interval: Maximum check interval in seconds (default: 1800 = 30 minutes)
            idle_threshold: Number of idle checks before increasing interval (default: 3)
        """
        super().__init__(config, min_interval)
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.idle_threshold = idle_threshold
        self.idle_count = 0
        self.current_interval = min_interval
        
        logger.info(f"Smart watch mode initialized")
        logger.info(f"  Min interval: {min_interval}s ({min_interval // 60}m)")
        logger.info(f"  Max interval: {max_interval}s ({max_interval // 60}m)")
        logger.info(f"  Idle threshold: {idle_threshold} checks")
    
    def run(self) -> None:
        """Run agent in smart watch mode with adaptive intervals."""
        logger.info("=" * 60)
        logger.info("GitHub AI Agent - SMART WATCH MODE")
        logger.info(f"Organization: {self.config.github_organization}")
        logger.info("=" * 60)
        logger.info("\n🔄 Agent is now in SMART STANDBY mode...")
        logger.info("Check interval adapts based on activity")
        logger.info("Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                logger.info("=" * 60)
                logger.info(f"Check #{iteration} - {current_time}")
                logger.info(f"Current interval: {self.current_interval}s ({self.current_interval // 60}m)")
                logger.info("=" * 60)
                
                try:
                    # Run agent to check for new work
                    logger.info("Checking for new issues and PRs...")
                    
                    # Capture if there was any work done
                    exit_code = self.agent.run()
                    
                    # Check if there was work (simplified - could be improved)
                    # For now, assume work was done if exit_code is 0
                    # In a real implementation, we'd check the actual results
                    
                    if exit_code == 0:
                        logger.info("✓ Check completed successfully")
                        # Reset to min interval if work was found
                        # (This is simplified - in production, check actual work done)
                        self.idle_count = 0
                        self.current_interval = self.min_interval
                    else:
                        logger.warning(f"⚠ Check completed with errors")
                        self.idle_count += 1
                    
                except Exception as e:
                    logger.error(f"Error during check: {e}", exc_info=True)
                    self.idle_count += 1
                
                # Adjust interval based on idle count
                if self.idle_count >= self.idle_threshold:
                    # Increase interval (but don't exceed max)
                    new_interval = min(self.current_interval * 2, self.max_interval)
                    if new_interval != self.current_interval:
                        logger.info(f"📈 No activity detected. Increasing check interval to {new_interval}s ({new_interval // 60}m)")
                        self.current_interval = new_interval
                
                # Wait before next check
                next_check = datetime.now()
                import datetime as dt
                next_check = next_check + dt.timedelta(seconds=self.current_interval)
                next_check_str = next_check.strftime("%H:%M:%S")
                
                logger.info(f"\n💤 Standby... Next check at {next_check_str}")
                logger.info(f"   (Waiting {self.current_interval} seconds / {self.current_interval // 60} minutes)")
                logger.info(f"   Idle count: {self.idle_count}/{self.idle_threshold}")
                logger.info("-" * 60 + "\n")
                
                time.sleep(self.current_interval)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("🛑 Smart watch mode stopped by user (Ctrl+C)")
            logger.info(f"Total checks performed: {iteration}")
            logger.info("=" * 60)
