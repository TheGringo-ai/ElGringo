"""
UI Agent - Autonomous UI Testing and Interaction
=================================================

Enables AI agents to autonomously interact with web UIs:
- Navigate and explore interfaces
- Click buttons, fill forms
- Take screenshots and analyze results
- Run automated test scenarios
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UIAction:
    """Represents a UI action taken by the agent."""
    action_type: str  # click, type, select, screenshot, wait
    target: str  # selector or description
    value: Optional[str] = None
    result: Optional[str] = None
    success: bool = True
    screenshot_path: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class UITestResult:
    """Result of an autonomous UI test."""
    test_name: str
    success: bool
    actions: List[UIAction]
    summary: str
    duration: float
    screenshots: List[str]
    errors: List[str]


class UIAgent:
    """
    Autonomous UI testing agent using Playwright.

    Can navigate web interfaces, interact with elements,
    and report results back to the AI team.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.actions: List[UIAction] = []
        self.screenshots_dir = os.path.expanduser("~/.ai-dev-team/screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    async def start(self):
        """Start the browser."""
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        logger.info("UI Agent browser started")

    async def stop(self):
        """Stop the browser."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("UI Agent browser stopped")

    async def navigate(self, url: str) -> UIAction:
        """Navigate to a URL."""
        action = UIAction(action_type="navigate", target=url)
        try:
            # Use 'load' instead of 'networkidle' for Gradio apps
            # Gradio maintains WebSocket connections that prevent networkidle
            await self.page.goto(url, wait_until="load", timeout=15000)
            # Wait for Gradio to initialize
            await self.page.wait_for_timeout(2000)
            action.result = f"Navigated to {url}"
            action.success = True
        except Exception as e:
            # Try with domcontentloaded as fallback
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=10000)
                await self.page.wait_for_timeout(2000)
                action.result = f"Navigated to {url} (fallback)"
                action.success = True
            except Exception as e2:
                action.result = f"Failed to navigate: {e2}"
                action.success = False
        self.actions.append(action)
        return action

    async def click(self, selector: str, description: str = "") -> UIAction:
        """Click an element."""
        action = UIAction(action_type="click", target=selector, value=description)
        try:
            await self.page.click(selector, timeout=5000)
            await self.page.wait_for_timeout(500)  # Brief wait for UI update
            action.result = f"Clicked: {description or selector}"
            action.success = True
        except Exception as e:
            action.result = f"Failed to click: {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def click_text(self, text: str) -> UIAction:
        """Click element containing specific text."""
        action = UIAction(action_type="click_text", target=text)
        try:
            await self.page.get_by_text(text, exact=False).first.click(timeout=5000)
            await self.page.wait_for_timeout(500)
            action.result = f"Clicked text: {text}"
            action.success = True
        except Exception as e:
            action.result = f"Failed to click text '{text}': {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def click_button(self, button_text: str) -> UIAction:
        """Click a button by its text."""
        action = UIAction(action_type="click_button", target=button_text)
        try:
            # Use JavaScript to click buttons - Gradio has overlapping elements
            clicked = await self.page.evaluate(f"""
                () => {{
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {{
                        if (btn.textContent.includes('{button_text}')) {{
                            btn.click();
                            return true;
                        }}
                    }}
                    // Also check for elements with role="button"
                    const roleButtons = document.querySelectorAll('[role="button"]');
                    for (const btn of roleButtons) {{
                        if (btn.textContent.includes('{button_text}')) {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if clicked:
                await self.page.wait_for_timeout(500)
                action.result = f"Clicked button: {button_text}"
                action.success = True
            else:
                action.result = f"Button '{button_text}' not found"
                action.success = False
        except Exception as e:
            action.result = f"Failed to click button '{button_text}': {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def fill(self, selector: str, value: str, description: str = "") -> UIAction:
        """Fill a text input."""
        action = UIAction(action_type="fill", target=selector, value=value)
        try:
            await self.page.fill(selector, value, timeout=5000)
            action.result = f"Filled {description or selector} with value"
            action.success = True
        except Exception as e:
            action.result = f"Failed to fill: {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def fill_by_label(self, label: str, value: str) -> UIAction:
        """Fill input by its label text."""
        action = UIAction(action_type="fill_label", target=label, value=value)
        try:
            await self.page.get_by_label(label).fill(value, timeout=5000)
            action.result = f"Filled '{label}' with value"
            action.success = True
        except Exception as e:
            action.result = f"Failed to fill '{label}': {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def select_tab(self, tab_name: str) -> UIAction:
        """Select a tab in Gradio interface, handling overflow menus."""
        action = UIAction(action_type="select_tab", target=tab_name)
        try:
            # First: Try clicking visible tab directly
            tab_locator = self.page.locator(f'button[role="tab"]:has-text("{tab_name}")')
            if await tab_locator.count() > 0:
                await tab_locator.first.click(force=True, timeout=3000)
                await self.page.wait_for_timeout(500)
                action.result = f"Selected tab: {tab_name}"
                action.success = True
                self.actions.append(action)
                return action

            # Second: Check if tab is in overflow menu
            overflow_menu = self.page.locator('.overflow-menu').first
            if await overflow_menu.count() > 0:
                # Click overflow menu to show dropdown
                await overflow_menu.click(force=True, timeout=2000)
                await self.page.wait_for_timeout(300)

                # Now click the tab in the dropdown
                dropdown_tab = self.page.locator(f'.overflow-dropdown button:has-text("{tab_name}")')
                if await dropdown_tab.count() > 0:
                    await dropdown_tab.first.click(force=True, timeout=2000)
                    await self.page.wait_for_timeout(500)
                    action.result = f"Selected tab from overflow: {tab_name}"
                    action.success = True
                    self.actions.append(action)
                    return action

            # Third: Try any button with exact text match
            btn_locator = self.page.get_by_text(tab_name, exact=True).first
            if await btn_locator.count() > 0:
                await btn_locator.click(force=True, timeout=3000)
                await self.page.wait_for_timeout(500)
                action.result = f"Selected tab: {tab_name}"
                action.success = True
                self.actions.append(action)
                return action

            action.result = f"Tab '{tab_name}' not found"
            action.success = False
        except Exception as e:
            action.result = f"Failed to select tab '{tab_name}': {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def screenshot(self, name: str = "screenshot") -> UIAction:
        """Take a screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)

        action = UIAction(action_type="screenshot", target=name)
        try:
            await self.page.screenshot(path=filepath, full_page=True)
            action.result = f"Screenshot saved: {filepath}"
            action.screenshot_path = filepath
            action.success = True
        except Exception as e:
            action.result = f"Failed to take screenshot: {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def get_text(self, selector: str) -> str:
        """Get text content of an element."""
        try:
            return await self.page.text_content(selector, timeout=5000) or ""
        except Exception:
            return ""

    async def wait_for(self, selector: str, timeout: int = 5000) -> UIAction:
        """Wait for an element to appear."""
        action = UIAction(action_type="wait", target=selector)
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            action.result = f"Element found: {selector}"
            action.success = True
        except Exception as e:
            action.result = f"Timeout waiting for {selector}: {e}"
            action.success = False
        self.actions.append(action)
        return action

    async def get_page_content(self) -> Dict[str, Any]:
        """Get information about the current page."""
        try:
            title = await self.page.title()
            url = self.page.url

            # Get visible text (simplified)
            body_text = await self.page.inner_text("body")

            # Get all buttons
            buttons = await self.page.get_by_role("button").all_text_contents()

            # Get all tabs
            tabs = await self.page.get_by_role("tab").all_text_contents()

            return {
                "title": title,
                "url": url,
                "buttons": buttons[:20],  # Limit
                "tabs": tabs[:20],
                "text_preview": body_text[:1000] if body_text else ""
            }
        except Exception as e:
            return {"error": str(e)}

    def get_action_summary(self) -> str:
        """Get summary of all actions taken."""
        lines = ["## UI Agent Action Summary\n"]
        for i, action in enumerate(self.actions, 1):
            status = "✅" if action.success else "❌"
            lines.append(f"{i}. {status} **{action.action_type}**: {action.target}")
            if action.result:
                lines.append(f"   → {action.result}")
            if action.screenshot_path:
                lines.append(f"   📸 {action.screenshot_path}")
        return "\n".join(lines)


class AITeamUITester:
    """
    High-level UI testing interface for the AI Team.

    Provides pre-built test scenarios and autonomous testing capabilities.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:7861"):
        self.base_url = base_url
        self.agent = None

    async def test_git_panel(self) -> UITestResult:
        """Test the Git panel functionality."""
        start_time = asyncio.get_event_loop().time()
        errors = []
        screenshots = []

        self.agent = UIAgent(headless=True)
        await self.agent.start()

        try:
            # Navigate to the app
            await self.agent.navigate(self.base_url)
            await self.agent.page.wait_for_timeout(2000)  # Wait for Gradio to load

            # Take initial screenshot
            ss = await self.agent.screenshot("git_panel_01_initial")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click on Git tab
            await self.agent.select_tab("🔀 Git")
            await self.agent.page.wait_for_timeout(500)

            # Take screenshot of Git panel
            ss = await self.agent.screenshot("git_panel_02_tab_selected")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click Status button
            await self.agent.click_button("📊 Status")
            await self.agent.page.wait_for_timeout(1000)

            # Take screenshot of status output
            ss = await self.agent.screenshot("git_panel_03_status_output")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click List Branches button
            await self.agent.click_button("🔄 List Branches")
            await self.agent.page.wait_for_timeout(500)

            ss = await self.agent.screenshot("git_panel_04_branches")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click Show Log button
            await self.agent.click_button("📜 Show Log")
            await self.agent.page.wait_for_timeout(500)

            ss = await self.agent.screenshot("git_panel_05_log")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

        except Exception as e:
            errors.append(str(e))
        finally:
            await self.agent.stop()

        duration = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0 and all(a.success for a in self.agent.actions)

        return UITestResult(
            test_name="Git Panel Test",
            success=success,
            actions=self.agent.actions,
            summary=self.agent.get_action_summary(),
            duration=duration,
            screenshots=screenshots,
            errors=errors
        )

    async def test_docker_panel(self) -> UITestResult:
        """Test the Docker panel functionality."""
        start_time = asyncio.get_event_loop().time()
        errors = []
        screenshots = []

        self.agent = UIAgent(headless=True)
        await self.agent.start()

        try:
            await self.agent.navigate(self.base_url)
            await self.agent.page.wait_for_timeout(2000)

            # Click on Docker tab
            await self.agent.select_tab("🐳 Docker")
            await self.agent.page.wait_for_timeout(500)

            ss = await self.agent.screenshot("docker_panel_01_tab")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click Containers button
            await self.agent.click_button("📋 Containers")
            await self.agent.page.wait_for_timeout(1000)

            ss = await self.agent.screenshot("docker_panel_02_containers")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click Images button
            await self.agent.click_button("🖼️ Images")
            await self.agent.page.wait_for_timeout(1000)

            ss = await self.agent.screenshot("docker_panel_03_images")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

        except Exception as e:
            errors.append(str(e))
        finally:
            await self.agent.stop()

        duration = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0

        return UITestResult(
            test_name="Docker Panel Test",
            success=success,
            actions=self.agent.actions,
            summary=self.agent.get_action_summary(),
            duration=duration,
            screenshots=screenshots,
            errors=errors
        )

    async def test_environment_panel(self) -> UITestResult:
        """Test the Environment panel functionality."""
        start_time = asyncio.get_event_loop().time()
        errors = []
        screenshots = []

        self.agent = UIAgent(headless=True)
        await self.agent.start()

        try:
            await self.agent.navigate(self.base_url)
            await self.agent.page.wait_for_timeout(2000)

            # Click on Env tab
            await self.agent.select_tab("⚙️ Env")
            await self.agent.page.wait_for_timeout(500)

            ss = await self.agent.screenshot("env_panel_01_tab")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click Load .env button
            await self.agent.click_button("📂 Load .env")
            await self.agent.page.wait_for_timeout(1000)

            ss = await self.agent.screenshot("env_panel_02_loaded")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

            # Click Validate button
            await self.agent.click_button("✅ Validate")
            await self.agent.page.wait_for_timeout(500)

            ss = await self.agent.screenshot("env_panel_03_validated")
            if ss.screenshot_path:
                screenshots.append(ss.screenshot_path)

        except Exception as e:
            errors.append(str(e))
        finally:
            await self.agent.stop()

        duration = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0

        return UITestResult(
            test_name="Environment Panel Test",
            success=success,
            actions=self.agent.actions,
            summary=self.agent.get_action_summary(),
            duration=duration,
            screenshots=screenshots,
            errors=errors
        )

    async def test_all_panels(self) -> Dict[str, UITestResult]:
        """Run all panel tests."""
        results = {}

        print("🤖 AI Agent Testing: Git Panel...")
        results["git"] = await self.test_git_panel()

        print("🤖 AI Agent Testing: Docker Panel...")
        results["docker"] = await self.test_docker_panel()

        print("🤖 AI Agent Testing: Environment Panel...")
        results["environment"] = await self.test_environment_panel()

        return results


async def run_ai_agent_tests(base_url: str = "http://127.0.0.1:7861"):
    """
    Run autonomous AI agent UI tests.

    This function is called by the AI team to test the UI.
    """
    tester = AITeamUITester(base_url)
    results = await tester.test_all_panels()

    print("\n" + "=" * 60)
    print("🤖 AI AGENT TEST RESULTS")
    print("=" * 60)

    for name, result in results.items():
        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"\n{name.upper()}: {status} ({result.duration:.1f}s)")
        print(result.summary)

        if result.errors:
            print(f"\nErrors: {result.errors}")

        if result.screenshots:
            print(f"\nScreenshots saved:")
            for ss in result.screenshots:
                print(f"  📸 {ss}")

    return results


# Quick test function
if __name__ == "__main__":
    asyncio.run(run_ai_agent_tests())
