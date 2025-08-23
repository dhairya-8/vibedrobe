from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
        
# Example for usage of terminal debugger
# one-line usage (shows simple messages)
# error("Database connection failed!")
# success("User created successfully")
# info("Processing user data...")

# # Detailed usage (shows nice boxes)
# error("Database connection failed!", detailed=True)
# success("User created successfully", detailed=True)
# info("Processing user data...", detailed=True)

class TerminalColors:
    """ANSI color codes for terminal styling"""
    RED = '\033[31m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_BLUE = '\033[94m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class TerminalDebugger:
    """Simple terminal debugger for Django projects"""
    
    def __init__(self):
        self.colors = TerminalColors()
    
    def _format_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def _create_box(self, content, title, color, width=60):
        """Create a consistent box around content"""
        timestamp = f"Time: {self._format_timestamp()}"
        
        # Split content but exclude timestamp for width calculation
        content_lines = [line for line in content.split('\n') if not line.startswith('Time:')]
        max_content_width = max(len(line) for line in content_lines) if content_lines else 0
        box_width = max(width, max_content_width + 4, len(title) + 4, len(timestamp) + 4)
        
        # Create box with consistent width
        horizontal_line = "━" * (box_width - 2)
        top_border = f"{color}┏{horizontal_line}┓{self.colors.RESET}"
        bottom_border = f"{color}┗{horizontal_line}┛{self.colors.RESET}"
        
        # Title line - centered
        title_padding = box_width - len(title) - 4
        left_padding = title_padding // 2
        right_padding = title_padding - left_padding
        title_line = f"{color}┃{' ' * left_padding} {self.colors.WHITE}{self.colors.BOLD}{title}{self.colors.RESET} {' ' * right_padding}{color}┃{self.colors.RESET}"
        
        # Content lines with consistent padding
        formatted_lines = [top_border, title_line]
        
        for line in content_lines:
            padding = box_width - len(line) - 4
            content_line = f"{color}┃{self.colors.RESET} {color}{line}{self.colors.RESET}{' ' * padding} {color}┃{self.colors.RESET}"
            formatted_lines.append(content_line)
        
        # Footer line - timestamp centered
        footer_padding = box_width - len(timestamp) - 4
        footer_left_padding = footer_padding // 2
        footer_right_padding = footer_padding - footer_left_padding
        footer_line = f"{color}┃{' ' * footer_left_padding} {self.colors.WHITE}{timestamp}{self.colors.RESET} {' ' * footer_right_padding}{color}┃{self.colors.RESET}"
        
        formatted_lines.append(footer_line)
        formatted_lines.append(bottom_border)
        return '\n'.join(formatted_lines)
    
    def error(self, message, detailed=False):
        """Print error message"""
        if detailed:
            formatted = self._create_box(message, "ERROR", self.colors.BRIGHT_RED)
        else:
            timestamp = self._format_timestamp()
            formatted = f"\n{self.colors.BRIGHT_RED}{'─' * 60}{self.colors.RESET}\n{self.colors.BRIGHT_RED}✖ ERROR {timestamp}{self.colors.RESET}\n{self.colors.BRIGHT_RED}{message}{self.colors.RESET}\n{self.colors.BRIGHT_RED}{'─' * 60}{self.colors.RESET}\n"
        
        print(formatted)
    
    def success(self, message, detailed=False):
        """Print success message"""
        if detailed:
            formatted = self._create_box(message, "SUCCESS", self.colors.BRIGHT_GREEN)
        else:
            timestamp = self._format_timestamp()
            formatted = f"\n{self.colors.BRIGHT_GREEN}{'─' * 60}{self.colors.RESET}\n{self.colors.BRIGHT_GREEN}✓ SUCCESS {timestamp}{self.colors.RESET}\n{self.colors.BRIGHT_GREEN}{message}{self.colors.RESET}\n{self.colors.BRIGHT_GREEN}{'─' * 60}{self.colors.RESET}\n"
        
        print(formatted)
    
    def info(self, message, detailed=False):
        """Print info message"""
        if detailed:
            formatted = self._create_box(message, "INFO", self.colors.BRIGHT_BLUE)
        else:
            timestamp = self._format_timestamp()
            formatted = f"\n{self.colors.BRIGHT_BLUE}{'─' * 60}{self.colors.RESET}\n{self.colors.BRIGHT_BLUE}ℹ INFO {timestamp}{self.colors.RESET}\n{self.colors.BRIGHT_BLUE}{message}{self.colors.RESET}\n{self.colors.BRIGHT_BLUE}{'─' * 60}{self.colors.RESET}\n"
        
        print(formatted)


# Create a global instance for easy usage
console = TerminalDebugger()

# Convenience functions for quick usage
def error(message, detailed=False):
    """Quick error print"""
    console.error(message, detailed)

def success(message, detailed=False):
    """Quick success print"""
    console.success(message, detailed)

def info(message, detailed=False):
    """Quick info print"""
    console.info(message, detailed)