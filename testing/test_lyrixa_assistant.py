"""
Test script to verify the functionality of lyrixa_chat.py in a real application context.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# print("Testing lyrixa_chat.py module imports...")
try:
    from Lyrixa.ui.aether_chat import (
        LyrixaAssistantInterface,
        create_embeddable_aetherchat,
    )

    print("✓ Successfully imported LyrixaAssistantInterface and create_embeddable_aetherchat")

    # Try to create a chat widget using the function
    try:
        chat_widget = create_embeddable_aetherchat()
        print("✓ Successfully created embeddable AetherraChat widget")
    except Exception as e:
        print(f"✗ Error creating embeddable AetherraChat widget: {e}")

    # Try to create a LyrixaAssistantInterface instance (will only work if PySide6 is available)
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        chat = LyrixaAssistantInterface()
        print("✓ Successfully created LyrixaAssistantInterface instance")
    except ImportError:
        print("ℹ PySide6 not available, skipping LyrixaAssistantInterface instantiation")
    except Exception as e:
        print(f"✗ Error creating LyrixaAssistantInterface instance: {e}")
except Exception as e:
    print(f"✗ Error importing from aetherra_chat.py: {e}")

print("\nLyrixaChat testing complete.")
