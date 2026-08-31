from pathlib import Path
from time import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import threading
import pyperclip
import time

# ============================================================
# CONFIGURATION
# ============================================================

 
URL = "https://chatgpt.com/"

 
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "output.txt"
INPUT_FILE = BASE_DIR / "input.txt"

# Playwright timeout: 30 seconds
TIMEOUT = 30000


# ============================================================
# HELPER: FIND FIRST WORKING SELECTOR
# ============================================================

def find_first(page, selectors):
    

    for selector in selectors:
        try:
            locator = page.locator(selector)

            if locator.count() > 0 and locator.first.is_visible():
                print(f"[FOUND] {selector}")
                return locator.first

        except Exception:
            pass

    return None


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_output(text):
   

    OUTPUT_FILE.write_text(
        text,
        encoding="utf-8"
    )

    print(f"\n[SAVED] Response saved to:")
    print(OUTPUT_FILE)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("        LOCAL CHATGPT DEMO BRIDGE")
    print("=" * 60)
    print(f"URL: {URL}")
    print("Type 'exit' to close the program.\n")

    with sync_playwright() as p:

        # ----------------------------------------------------
        # Launch Chromium
        # ----------------------------------------------------

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        page.set_default_timeout(TIMEOUT)

        print("[INFO] Opening localhost page...")

        try:

            page.goto(
                URL,
                wait_until="domcontentloaded"
            )

            print("[OK] Page loaded.\n")

        except Exception as error:

            print("\n[ERROR] Could not open localhost page.")
            print(error)

            browser.close()
            return


        # ====================================================
        # FIND MESSAGE INPUT
        # ====================================================

        input_selectors = ["textarea"]

        message_box = find_first(
            page,
            input_selectors
        )

        if message_box is None:

            print("\n[ERROR] Message input was NOT found.")

            print("\nAvailable page inputs:")

            elements = page.locator("textarea")

            count = elements.count()

            print(f"Found {count} possible input elements.")

            for i in range(count):

                try:
                    element = elements.nth(i)

                    print(
                        f"\nElement {i}:"
                    )

                    print(
                        element.evaluate(
                            "(el) => el.outerHTML"
                        )
                    )

                except Exception:
                    pass

            print(
                "\nFix the HTML selector and run again."
            )

            input("\nPress Enter to close...")

            browser.close()
            return


        # ====================================================
        # FIND SEND BUTTON
        # ====================================================

        send_selectors = ["button[aria-label='Send message']"]

        send_button = find_first(
            page,
            send_selectors
        )

        if send_button is None:
            print(
                "[WARNING] Send message button is not visible yet; "
                "will retry after filling the textarea."
            )


        # ====================================================
        # CHAT LOOP
        # ====================================================

        print("\n" + "=" * 60)
        print("[READY] Browser automation is ready.")
        print("[READY] Watching input.txt for changes.")
        print("=" * 60)

        # Create input.txt if it does not exist
        INPUT_FILE.touch(exist_ok=True)

        # Remember the current modification timestamp
        last_modified_time = INPUT_FILE.stat().st_mtime

        while True:
            # ------------------------------------------------
            # WATCH input.txt FOR CHANGES
            # ------------------------------------------------

            try:
                current_modified_time = INPUT_FILE.stat().st_mtime

            except FileNotFoundError:
                INPUT_FILE.touch()
                last_modified_time = INPUT_FILE.stat().st_mtime
                time.sleep(0.5)
                continue

            # File has not changed -> do nothing
            if current_modified_time == last_modified_time:
                time.sleep(0.5)
                continue

            # File changed -> remember the new timestamp
            last_modified_time = current_modified_time

            # Read the new prompt
            try:
                prompt = INPUT_FILE.read_text(
                    encoding="utf-8"
                ).strip()

            except Exception as error:
                print(f"[ERROR] Could not read input.txt: {error}")
                time.sleep(0.5)
                continue


            # Ignore empty updates
            if not prompt:
                print("[INFO] input.txt changed but is empty.")
                time.sleep(0.5)
                continue


            print("\n[INFO] input.txt changed.")
            print(f"[INFO] New prompt detected: {prompt!r}")


            try:

                # --------------------------------------------
                # FIND EXISTING COPY BUTTONS
                # --------------------------------------------

                def get_copy_buttons():

                    return page.locator(
                        "button[aria-label='Copy response']"
                    )


                copy_buttons = get_copy_buttons()

                # Number of Copy buttons BEFORE sending
                old_copy_count = copy_buttons.count()
                print(f"[INFO] Existing Copy response buttons: {old_copy_count}")


                # --------------------------------------------
                # FILL MESSAGE
                # --------------------------------------------

                print("[INFO] Typing message...")

                message_box.click()
                message_box.fill(
                    prompt
                )

                if message_box.input_value() != prompt:
                    raise Exception("Prompt was not inserted into textarea.")


                # --------------------------------------------
                # SEND MESSAGE
                # --------------------------------------------

                print("[INFO] Clicking Send message...")

                send_button = page.locator(
                    "button[aria-label='Send message']"
                ).last

                if send_button.count() == 0:
                    print("[WARNING] Send message button unavailable; using Enter.")
                    message_box.press("Enter")
                else:
                    send_button.wait_for(state="visible", timeout=TIMEOUT)
                    if not send_button.is_enabled():
                        raise Exception("Send message button is disabled.")
                    send_button.click()

                print("[INFO] Prompt sent.")


                # --------------------------------------------
                # WAIT FOR NEW RESPONSE
                # --------------------------------------------

                print("[INFO] Waiting for response...")

                page.wait_for_function(
                    """
                    (oldCount) => document.querySelectorAll(
                        'button[aria-label="Copy response"]'
                    ).length > oldCount
                    """,
                    arg=old_copy_count,
                    timeout=120000
                )

                print("[FOUND] New Copy response button.")
                page.wait_for_timeout(400)


                # --------------------------------------------
                # GET LATEST COPY BUTTON
                # --------------------------------------------

                copy_buttons = get_copy_buttons()

                copy_count = copy_buttons.count()

                if copy_count == 0:

                    raise Exception(
                        "Copy button was not found."
                    )


                latest_copy_button = copy_buttons.last
                latest_copy_button.wait_for(state="visible", timeout=TIMEOUT)

                if not latest_copy_button.is_enabled():
                    raise Exception("Latest Copy response button is disabled.")

                print("[FOUND] Latest Copy response button.")


                # --------------------------------------------
                # CLICK COPY BUTTON
                # --------------------------------------------

                latest_copy_button.click()

                print("[INFO] Copy response button clicked.")


                # Give clipboard a moment to update
                page.wait_for_timeout(500)


                # --------------------------------------------
                # READ WINDOWS CLIPBOARD
                # --------------------------------------------

                print("[INFO] Reading clipboard...")
                response = pyperclip.paste().strip()


                if not response:

                    raise Exception(
                        "Clipboard was empty after clicking Copy."
                    )


                # --------------------------------------------
                # DISPLAY RESPONSE
                # --------------------------------------------

                print("\nAssistant:")
                print("-" * 60)

                print(response)

                print("-" * 60)


                # --------------------------------------------
                # SAVE / OVERWRITE output.txt
                # --------------------------------------------

                save_output(response)


            except PlaywrightTimeoutError:

                print(
                    "\n[ERROR] Timed out waiting for a new ChatGPT response."
                )

                print(
                    f"Current page URL: {page.url}"
                )

                print(
                    f"Textarea count: {page.locator('textarea').count()}"
                )

                print(
                    "Send message button count: "
                    + str(page.locator("button[aria-label='Send message']").count())
                )

                print(
                    "Copy response button count: "
                    + str(page.locator("button[aria-label='Copy response']").count())
                    + f" (before request: {old_copy_count})"
                )


            except Exception as error:

                print(
                    "\n[ERROR]"
                )

                print(error)


        # ====================================================
        # CLOSE
        # ====================================================

        print("\n[INFO] Closing browser...")

        browser.close()

        print("[DONE] Bridge stopped.")


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    main()
