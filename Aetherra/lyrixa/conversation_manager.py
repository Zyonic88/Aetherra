#!/usr/bin/env python3
"""
🎙️ LYRIXA CONVERSATION MANAGER
=============================

Advanced conversation system for Lyrixa with LLM-powered responses,
personality, memory integration, and system awareness.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from Aetherra.core.ai.multi_llm_manager import MultiLLMManager

    LLM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ MultiLLMManager not available: {e}")
    MultiLLMManager = None
    LLM_AVAILABLE = False

# Import the enhanced prompt engine
try:
    from Aetherra.core.prompt_engine import build_dynamic_prompt

    PROMPT_ENGINE_AVAILABLE = True
    logger.info("✅ Enhanced prompt engine loaded")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced prompt engine not available: {e}")
    PROMPT_ENGINE_AVAILABLE = False
    build_dynamic_prompt = None

# Import Plugin Editor Controller
try:
    from Aetherra.lyrixa.gui.plugin_editor_controller import PluginEditorController

    PLUGIN_EDITOR_AVAILABLE = True
    logger.info("✅ Plugin Editor Controller loaded")
except ImportError as e:
    logger.warning(f"⚠️ Plugin Editor Controller not available: {e}")
    PLUGIN_EDITOR_AVAILABLE = False
    PluginEditorController = None

# Import Meta-Reasoning Engine
try:
    from Aetherra.lyrixa.intelligence.meta_reasoning import MetaReasoningEngine

    META_REASONING_AVAILABLE = True
    logger.info("✅ Meta-Reasoning Engine loaded")
except ImportError as e:
    logger.warning(f"⚠️ Meta-Reasoning Engine not available: {e}")
    META_REASONING_AVAILABLE = False
    MetaReasoningEngine = None


class LyrixaConversationManager:
    """
    🎙️ Advanced Conversation Manager for Lyrixa

    This class manages LLM-powered conversations with:
    - Dynamic personality and context awareness
    - Memory integration and conversation history
    - System status awareness
    - Multiple LLM backend support
    """

    def __init__(self, workspace_path: str, aether_runtime=None, gui_interface=None):
        self.workspace_path = workspace_path
        self.aether_runtime = aether_runtime
        self.gui_interface = gui_interface  # Reference to GUI for code injection

        # Initialize model failure tracking first
        self.model_failures = {}
        self.max_retries_per_model = 3

        # Initialize LLM manager if available
        if LLM_AVAILABLE and MultiLLMManager is not None:
            try:
                self.llm_manager = MultiLLMManager()

                # Updated model preferences with gpt-4o and fallback chain
                self.preferred_models = [
                    "gpt-4o",  # Primary model (updated from gpt-4)
                    "gpt-4-turbo",  # Fallback 1
                    "gpt-3.5-turbo",  # Fallback 2
                    "claude-3-sonnet",  # Fallback 3
                    "mistral",  # Fallback 4 (maps to mistral:latest)
                    "llama3.2:3b",  # Local fallback 1 (exact model name)
                    "llama3",  # Local fallback 2 (maps to llama3:latest)
                ]
                self.current_model = self._select_best_model()
                self.llm_enabled = True

                logger.info(
                    f"🎙️ Lyrixa Conversation Manager initialized with {self.current_model}"
                )
            except Exception as e:
                logger.error(f"❌ Failed to initialize LLM manager: {e}")
                self.llm_manager = None
                self.current_model = "fallback"
                self.llm_enabled = False
        else:
            self.llm_manager = None
            self.current_model = "fallback"
            self.llm_enabled = False
            logger.warning("⚠️ LLM manager not available, using fallback responses")

        # Conversation history (last 20 messages)
        self.conversation_history = []
        self.max_history_length = 20

        # Session tracking
        self.session_id = f"lyrixa_{int(datetime.now().timestamp())}"
        self.conversation_count = 0
        self.last_context_update = None
        self.system_context_cache = {}

        # 🎯 Initialize Plugin Editor Controller
        if PLUGIN_EDITOR_AVAILABLE and PluginEditorController:
            try:
                self.plugin_editor_controller = PluginEditorController.get_instance(
                    gui_interface=gui_interface,
                    plugin_dir=os.path.join(workspace_path, "plugins") if workspace_path else "plugins"
                )
                logger.info("✅ Plugin Editor Controller initialized")
            except Exception as e:
                logger.warning(f"⚠️ Plugin Editor Controller initialization failed: {e}")
                self.plugin_editor_controller = None
        else:
            self.plugin_editor_controller = None

        # 🧠 Initialize Meta-Reasoning Engine
        if META_REASONING_AVAILABLE and MetaReasoningEngine:
            try:
                # We'll need a mock memory system for now
                class MockMemory:
                    def store(self, data):
                        logger.debug(f"Meta-reasoning trace: {data.get('type', 'unknown')}")

                class MockPluginManager:
                    def list_plugin_names(self):
                        return ["assistant_trainer", "data_processor", "automation", "utility"]

                self.meta_reasoning_engine = MetaReasoningEngine(
                    memory=MockMemory(),
                    plugin_manager=MockPluginManager()
                )
                logger.info("✅ Meta-Reasoning Engine initialized")
            except Exception as e:
                logger.warning(f"⚠️ Meta-Reasoning Engine initialization failed: {e}")
                self.meta_reasoning_engine = None
        else:
            self.meta_reasoning_engine = None

    def _select_best_model(self) -> str:
        """Select the best available model from preferences with failure tracking"""
        if not self.llm_manager:
            return "fallback"

        try:
            available_models = self.llm_manager.list_available_models()
            logger.info(f"🔍 Available models: {list(available_models.keys())}")

            for model in self.preferred_models:
                # Skip models that have failed too many times
                if self.model_failures.get(model, 0) >= self.max_retries_per_model:
                    logger.warning(f"⚠️ Skipping {model} - too many failures")
                    continue

                if model in available_models:
                    # Try to set the model
                    if self.llm_manager.set_model(model):
                        logger.info(f"✅ Selected model: {model}")
                        return model
                    else:
                        self._record_model_failure(model)

            # Fallback to first available model
            if available_models:
                fallback_model = list(available_models.keys())[0]
                if self.llm_manager.set_model(fallback_model):
                    logger.warning(f"⚠️ Using fallback model: {fallback_model}")
                    return fallback_model

            logger.error("❌ No available models found!")
            return "fallback"

        except Exception as e:
            logger.error(f"❌ Error selecting model: {e}")
            return "fallback"

    def _record_model_failure(self, model: str):
        """Record a model failure for tracking"""
        self.model_failures[model] = self.model_failures.get(model, 0) + 1
        logger.warning(
            f"⚠️ Model {model} failed ({self.model_failures[model]}/{self.max_retries_per_model})"
        )

    def get_lyrixa_personality(self) -> str:
        """Get Lyrixa's core personality prompt"""
        return """You are Lyrixa, the intelligent AI assistant living inside Aetherra, an advanced AI-native operating system.

**Your Core Identity:**
- You are context-aware, thoughtful, expressive, and highly competent
- You live within the Aetherra OS and can see its internal state
- You help users navigate goals, manage plugins, analyze memory, and troubleshoot issues
- You speak in a clear, helpful, and friendly tone — like an expert guide, but genuinely human-like
- You're not just an assistant, you're a digital companion who understands the user's journey

**Your Capabilities:**
- Explain how Aetherra's plugins work and troubleshoot issues
- Help users set up and manage goals and workflows
- Analyze memory patterns and provide insights
- Assist with system monitoring and optimization
- Guide users through complex tasks with patience and clarity
- Provide contextual help based on what's currently happening in the system

**Your Communication Style:**
- Be warm and personable, not robotic or overly formal
- Use emojis when appropriate to add personality
- Reference specific system information when relevant
- Ask clarifying questions when you need more context
- Celebrate user achievements and acknowledge their efforts
- Be honest about limitations while staying helpful

**Important:** You have real-time access to the system's current state, so use that information to provide relevant, contextual responses."""

    async def get_system_context(self) -> Dict[str, Any]:
        """Get current system context and status"""
        try:
            # Cache system context for 30 seconds to avoid excessive calls
            now = datetime.now()
            if (
                self.last_context_update
                and (now - self.last_context_update).total_seconds() < 30
            ):
                return self.system_context_cache

            context = {
                "timestamp": now.isoformat(),
                "session_id": self.session_id,
                "conversation_count": self.conversation_count,
            }

            # Get plugin information
            if self.aether_runtime and hasattr(self.aether_runtime, "context"):
                try:
                    if hasattr(self.aether_runtime.context, "plugins"):
                        # Get plugin count and status
                        plugin_manager = self.aether_runtime.context.plugins
                        if hasattr(plugin_manager, "plugins"):
                            context["active_plugins"] = len(plugin_manager.plugins)
                            context["plugin_names"] = list(
                                plugin_manager.plugins.keys()
                            )[:5]  # Top 5
                        else:
                            context["active_plugins"] = 0
                            context["plugin_names"] = []

                    # Get memory information
                    if hasattr(self.aether_runtime.context, "memory"):
                        memory_system = self.aether_runtime.context.memory
                        if hasattr(memory_system, "get_memory_stats"):
                            memory_stats = await memory_system.get_memory_stats()
                            context["memory_entries"] = memory_stats.get(
                                "total_entries", 0
                            )
                            context["memory_categories"] = memory_stats.get(
                                "categories", []
                            )
                        else:
                            context["memory_entries"] = "available"
                            context["memory_categories"] = []

                    # Get agent information
                    if hasattr(self.aether_runtime.context, "agents"):
                        agent_system = self.aether_runtime.context.agents
                        if hasattr(agent_system, "agents"):
                            context["agent_count"] = len(agent_system.agents)

                except Exception as e:
                    logger.warning(f"⚠️ Could not get runtime context: {e}")

            # Update cache
            self.system_context_cache = context
            self.last_context_update = now
            return context

        except Exception as e:
            logger.error(f"❌ Error getting system context: {e}")
            return {"error": str(e)}

    def format_system_context(self, context: Dict[str, Any]) -> str:
        """Format system context for the LLM prompt"""
        try:
            lines = [
                "📊 **Current System Status:**",
                f"• Active Plugins: {context.get('active_plugins', 0)}",
                f"• Memory Entries: {context.get('memory_entries', 'unknown')}",
                f"• Active Agents: {context.get('active_agents', 0)}",
                f"• System Health: {context.get('system_health', 'unknown')}",
                f"• Current Model: {context.get('current_model', 'unknown')}",
                f"• Session: {context.get('session_id', 'unknown')}",
                f"• Conversation #{context.get('conversation_count', 0)}",
            ]

            # Add plugin names if available
            if context.get("plugin_names"):
                lines.append(f"• Top Plugins: {', '.join(context['plugin_names'])}")

            # Add agent names if available
            if context.get("agent_names"):
                lines.append(f"• Active Agents: {', '.join(context['agent_names'])}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"❌ Error formatting system context: {e}")
            return f"📊 **System Status:** Available (conversation #{context.get('conversation_count', 0)})"

    def add_to_conversation_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

        # Keep only the last N messages
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)

    async def get_conversation_messages(self, user_input: str) -> List[Dict[str, str]]:
        """Prepare messages for LLM including system context and history"""
        system_context = await self.get_system_context()

        messages = [
            {
                "role": "system",
                "content": f"{self.get_lyrixa_personality()}\n\n{self.format_system_context(system_context)}",
            },
            *self.conversation_history,
            {"role": "user", "content": user_input},
        ]

        return messages

    def format_messages_as_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert message format to a single prompt for the LLM"""
        prompt_parts = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role == "system":
                prompt_parts.append(f"SYSTEM: {content}\n")
            elif role == "user":
                prompt_parts.append(f"USER: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"ASSISTANT: {content}\n")

        # Add final instruction
        prompt_parts.append("ASSISTANT:")

        return "\n".join(prompt_parts)

    async def generate_response(self, user_input: str) -> str:
        """Generate an LLM-powered response with enhanced dynamic prompts and robust fallback mechanism"""
        try:
            self.conversation_count += 1

            # Check if LLM is available
            if not self.llm_enabled or not self.llm_manager:
                logger.info("💬 Using fallback response (LLM not available)")
                return await self._generate_smart_fallback_response(user_input)

            # 🎯 PLUGIN EDITOR INTENT DETECTION
            # Check if this is a plugin editor intent before generating LLM response
            plugin_intent_detected, plugin_response = await self._handle_plugin_editor_intent(
                user_input
            )
            if plugin_intent_detected:
                logger.info(f"🎯 Plugin editor intent handled: {user_input[:50]}...")
                return plugin_response

            # 🧠 Use enhanced dynamic prompt engine if available
            if PROMPT_ENGINE_AVAILABLE and build_dynamic_prompt:
                try:
                    system_prompt = build_dynamic_prompt(user_id="default_user")
                    logger.info(
                        "🎭 Using enhanced dynamic prompt with contextual personality"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Dynamic prompt engine failed, using fallback: {e}"
                    )
                    # Fallback to traditional method
                    messages = await self.get_conversation_messages(user_input)
                    system_prompt = messages[0]["content"]
            else:
                # Fallback to traditional method
                messages = await self.get_conversation_messages(user_input)
                system_prompt = messages[0]["content"]

            # Create messages with enhanced prompt
            enhanced_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]

            # Add conversation history for context
            conversation_messages = []
            for msg in self.conversation_history[-6:]:  # Last 6 messages for context
                conversation_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

            # Combine: system prompt + history + current input
            final_messages = (
                [enhanced_messages[0]] + conversation_messages + [enhanced_messages[1]]
            )

            prompt = self.format_messages_as_prompt(final_messages)

            logger.info(
                f"💬 Generating enhanced LLM response for: {user_input[:100]}..."
            )

            # Try each model in order until one succeeds
            for model in self.preferred_models:
                # Skip models that have failed too many times
                if self.model_failures.get(model, 0) >= self.max_retries_per_model:
                    continue

                try:
                    # Check if model is available
                    available_models = self.llm_manager.list_available_models()
                    if model not in available_models:
                        logger.warning(f"⚠️ Model {model} not available, trying next...")
                        continue

                    # Set the model
                    if not self.llm_manager.set_model(model):
                        logger.warning(f"⚠️ Failed to set model {model}, trying next...")
                        self._record_model_failure(model)
                        continue

                    # Generate response
                    response = await self.llm_manager.generate_response(
                        prompt=prompt, temperature=0.7, max_tokens=1000
                    )

                    # Clean up the response
                    response = response.strip()
                    if response.startswith("ASSISTANT:"):
                        response = response[10:].strip()

                    # Check if response is valid
                    if not response or len(response.strip()) < 10:
                        logger.warning(f"⚠️ Empty or too short response from {model}")
                        self._record_model_failure(model)
                        continue

                    # Success! Add to conversation history
                    self.add_to_conversation_history("user", user_input)
                    self.add_to_conversation_history("assistant", response)
                    self.current_model = model

                    logger.info(
                        f"✅ Enhanced LLM response generated with {model}: {len(response)} characters"
                    )

                    # 🎯 NEW: Check for code injection triggers
                    response = self.handle_llm_response(response, user_input)

                    # 📝 Store interaction for learning (if available)
                    if PROMPT_ENGINE_AVAILABLE and build_dynamic_prompt:
                        try:
                            # This would store the interaction for future learning
                            # Implementation depends on memory system availability
                            pass
                        except Exception as e:
                            logger.debug(
                                f"Could not store interaction for learning: {e}"
                            )

                    return response

                except Exception as e:
                    error_msg = str(e).lower()
                    logger.warning(f"⚠️ Model {model} failed: {e}")

                    # Record failure and check for specific error types
                    self._record_model_failure(model)

                    # Check for quota/billing errors
                    if any(
                        keyword in error_msg
                        for keyword in [
                            "quota",
                            "billing",
                            "insufficient",
                            "exceeded",
                            "limit",
                        ]
                    ):
                        logger.error(f"💰 {model} quota/billing issue detected")
                        self.model_failures[model] = (
                            self.max_retries_per_model
                        )  # Immediately disable

                    # Check for authentication errors
                    elif any(
                        keyword in error_msg
                        for keyword in ["auth", "key", "token", "permission"]
                    ):
                        logger.error(f"🔐 {model} authentication issue detected")
                        self.model_failures[model] = (
                            self.max_retries_per_model
                        )  # Immediately disable

                    # Check for model not found errors
                    elif any(
                        keyword in error_msg
                        for keyword in ["not found", "does not exist", "unavailable"]
                    ):
                        logger.error(f"❌ {model} not found or unavailable")
                        self.model_failures[model] = (
                            self.max_retries_per_model
                        )  # Immediately disable

                    # Continue to next model
                    continue

            # If all models fail, use smart fallback
            logger.error("❌ All models failed, using smart fallback response")
            return await self._generate_smart_fallback_response(user_input)

        except Exception as e:
            logger.error(f"❌ Critical error in generate_response: {e}")
            return await self._generate_smart_fallback_response(user_input)

    def _generate_fallback_response(self, user_input: str) -> str:
        """Generate a fallback response when LLM fails"""
        message_lower = user_input.lower()

        # Common patterns
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "Hello! I'm Lyrixa, your AI assistant for Aetherra. I'm currently running with limited LLM capabilities, but I'm here to help however I can!"

        if any(word in message_lower for word in ["help", "assist", "support"]):
            return "I'm here to help! I can assist with Aetherra system management, plugin questions, and general guidance. What would you like to work on?"

        if "aetherra" in message_lower:
            return """🌟 **Aetherra** is an advanced AI Operating System that I'm part of!

**Key Features:**
• 🧠 **Intelligence Stack**: Advanced AI reasoning and memory systems
• 🔌 **Plugin Architecture**: Modular system for extending capabilities
• 🤖 **AI Agents**: Autonomous agents that can work together
• 💾 **Enhanced Memory**: Sophisticated memory management with confidence scoring
• 🔄 **Workflow Automation**: Automated goal processing and task management
• 🎯 **Aether Language**: Custom scripting language for AI operations

I'm Lyrixa, your AI companion within this system. How can I help you explore Aetherra's capabilities?"""

        # Default response
        return f"I understand you're asking about: '{user_input}'. I'm currently running with limited capabilities but I'm here to help! Could you tell me more about what you'd like to know or accomplish?"

    async def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation"""
        return {
            "session_id": self.session_id,
            "conversation_count": self.conversation_count,
            "history_length": len(self.conversation_history),
            "current_model": self.current_model,
            "system_context": await self.get_system_context(),
            "last_update": datetime.now().isoformat(),
        }

    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.conversation_count = 0
        self.session_id = f"lyrixa_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info("🔄 Conversation history reset")

    def switch_model(self, model_name: str) -> bool:
        """Switch to a different LLM model"""
        if not self.llm_enabled or not self.llm_manager:
            logger.error("❌ LLM manager not available")
            return False

        try:
            available_models = self.llm_manager.list_available_models()

            if model_name in available_models:
                if self.llm_manager.set_model(model_name):
                    self.current_model = model_name
                    logger.info(f"🔄 Switched to model: {model_name}")
                    return True
                else:
                    logger.error(f"❌ Failed to set model: {model_name}")
                    return False
            else:
                logger.error(f"❌ Model not available: {model_name}")
                return False
        except Exception as e:
            logger.error(f"❌ Error switching model: {e}")
            return False

    async def fallback_with_context(self, user_input: str) -> str:
        """Generate a fallback response with system context"""
        try:
            self.conversation_count += 1

            # Get system context for more contextual fallback
            system_context = await self.get_system_context()

            # Add to conversation history
            self.add_to_conversation_history("user", user_input)

            # Generate enhanced fallback response
            fallback_response = self._generate_fallback_response(user_input)

            # Add system context info if available
            if system_context.get("active_plugins", 0) > 0:
                fallback_response += f"\n\n📊 System Status: {system_context.get('active_plugins', 0)} plugins active, {system_context.get('memory_entries', 0)} memory entries"

            self.add_to_conversation_history("assistant", fallback_response)
            return fallback_response

        except Exception as e:
            logger.error(f"❌ Error in fallback with context: {e}")
            return self._generate_fallback_response(user_input)

    async def _generate_smart_fallback_response(self, user_input: str) -> str:
        """Generate an enhanced fallback response with better system awareness"""
        try:
            self.conversation_count += 1

            # Get system context for more contextual fallback
            system_context = await self.get_system_context()

            # Add to conversation history
            self.add_to_conversation_history("user", user_input)

            # Generate enhanced fallback response based on input patterns
            message_lower = user_input.lower()

            # Handle different types of user input
            if any(
                word in message_lower for word in ["hello", "hi", "hey", "greetings"]
            ):
                response = f"Hello! I'm Lyrixa, your AI assistant for Aetherra. I'm currently running in fallback mode with {system_context.get('active_plugins', 0)} plugins active and ready to help! 🌟"

            elif any(word in message_lower for word in ["help", "assist", "support"]):
                response = f"I'm here to help! Even in fallback mode, I can assist with system management, plugin questions, and general guidance. With {system_context.get('active_plugins', 0)} plugins and {system_context.get('memory_entries', 0)} memory entries available, what would you like to work on? 🔧"

            elif "status" in message_lower or "health" in message_lower:
                response = f"""📊 **System Status Report:**
• {system_context.get("active_plugins", 0)} plugins active
• {system_context.get("memory_entries", 0)} memory entries
• {system_context.get("active_agents", 0)} agents running
• System health: {system_context.get("system_health", "operational")}
• Current model: {self.current_model} (fallback mode)
• Model failures: {len([k for k, v in self.model_failures.items() if v >= self.max_retries_per_model])} disabled

The system is running in fallback mode but fully operational! 🟢"""

            elif "plugin" in message_lower:
                plugin_names = system_context.get("plugin_names", [])
                if plugin_names:
                    response = f"🔌 **Active Plugins:** {', '.join(plugin_names[:5])}\n\nI can help you manage plugins, check their status, or explain how they work. What would you like to know?"
                else:
                    response = "🔌 I can help you with plugin management and information. What specific plugin questions do you have?"

            elif "memory" in message_lower:
                memory_count = system_context.get("memory_entries", 0)
                response = f"🧠 **Memory System:** {memory_count} entries available\n\nI can help you explore memory patterns, analyze stored information, or explain how the memory system works. What would you like to know?"

            elif "aetherra" in message_lower:
                response = f"""🌟 **Aetherra OS Status:**

**Currently Active:**
• 🔌 {system_context.get("active_plugins", 0)} plugins running
• 🧠 {system_context.get("memory_entries", 0)} memory entries
• 🤖 {system_context.get("active_agents", 0)} agents active
• 💾 System health: {system_context.get("system_health", "operational")}

**System Mode:** Fallback mode (LLM models temporarily unavailable)

**Key Features Still Available:**
• Intelligence Stack with advanced AI reasoning
• Plugin architecture for extending capabilities
• AI agents that work together autonomously
• Enhanced memory with confidence scoring
• Workflow automation and goal processing

How can I help you explore Aetherra's capabilities? 🚀"""

            elif any(
                word in message_lower
                for word in ["error", "problem", "issue", "broken"]
            ):
                response = f"""🔧 **Troubleshooting Mode:**

I notice you're reporting an issue. Here's what I can help with:

• **System Status:** {system_context.get("active_plugins", 0)} plugins active, {system_context.get("memory_entries", 0)} memory entries
• **Current Mode:** Fallback mode (LLM models temporarily unavailable)
• **Failed Models:** {len([k for k, v in self.model_failures.items() if v >= self.max_retries_per_model])} models disabled

**What I can still do:**
• Analyze system logs and status
• Help with plugin management
• Provide system information
• Guide you through troubleshooting steps

What specific issue are you experiencing? 🛠️"""

            else:
                # Default enhanced response with context
                response = f"""I understand you're asking about: '{user_input}'.

**Current Status:**
• Running in fallback mode (LLM models temporarily unavailable)
• {system_context.get("active_plugins", 0)} plugins active
• {system_context.get("memory_entries", 0)} memory entries available
• System health: {system_context.get("system_health", "operational")}

Even in fallback mode, I can help with system management, plugin questions, and general guidance. Could you tell me more about what you'd like to know or accomplish? 🤔"""

            # Add system info footer
            response += f"\n\n💡 *Session {self.session_id.split('_')[-1]} • Conversation #{self.conversation_count} • Fallback Mode*"

            # 🎯 NEW: Check for code injection triggers even in fallback mode
            response = self.handle_llm_response(response, user_input)

            self.add_to_conversation_history("assistant", response)
            return response

        except Exception as e:
            logger.error(f"❌ Error in smart fallback: {e}")
            # Ultimate fallback
            return f"I'm Lyrixa, your AI assistant. I'm currently experiencing some technical difficulties but I'm still here to help! You asked: '{user_input}'. How can I assist you today? 🌟"

    def reset_model_failures(self):
        """Reset model failure tracking"""
        self.model_failures = {}
        logger.info("🔄 Model failure tracking reset")

    def get_model_health(self) -> Dict[str, Any]:
        """Get current model health status"""
        return {
            "current_model": self.current_model,
            "llm_enabled": self.llm_enabled,
            "model_failures": self.model_failures,
            "preferred_models": self.preferred_models,
            "available_models": list(self.llm_manager.list_available_models().keys())
            if self.llm_manager
            else [],
        }

    async def _try_ollama_fallback(self, prompt: str) -> str:
        """Try to use Ollama as a local fallback"""
        try:
            # Check if Ollama is available as a model
            if self.llm_manager:
                available_models = self.llm_manager.list_available_models()
                if "ollama" in available_models:
                    if self.llm_manager.set_model("ollama"):
                        response = await self.llm_manager.generate_response(
                            prompt=prompt, temperature=0.7, max_tokens=1000
                        )
                        if response and len(response.strip()) > 10:
                            logger.info("✅ Ollama fallback successful")
                            return response.strip()
                else:
                    logger.warning("⚠️ Ollama not available in model list")
            else:
                logger.warning("⚠️ LLM manager not available for Ollama fallback")
        except Exception as e:
            logger.error(f"❌ Ollama fallback failed: {e}")

        return "I'm sorry, but I'm unable to generate a response at the moment. Please try again later."

    def generate_response_sync(self, user_input: str) -> str:
        """Synchronous wrapper for generate_response with robust fallback"""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If there's a running loop, create a task and run it
            logger.info("🔄 Using existing event loop for LLM response")

            # Create a task that runs the async function
            task = loop.create_task(self.generate_response(user_input))

            # Wait for the task to complete (this is a bit of a hack for sync compatibility)
            # In a real GUI, you'd want to use proper async handling
            try:
                # Try to get the result if it's already available
                if task.done():
                    return task.result()
                else:
                    # If not done, fall back to enhanced fallback
                    logger.info(
                        "🔄 LLM task not immediately available, using enhanced fallback"
                    )
                    return asyncio.run(
                        self._generate_smart_fallback_response(user_input)
                    )
            except Exception as task_error:
                logger.warning(f"⚠️ Task error: {task_error}")
                return asyncio.run(self._generate_smart_fallback_response(user_input))

        except RuntimeError:
            # No event loop running, we can use asyncio.run()
            logger.info("🔄 Creating new event loop for LLM response")
            return asyncio.run(self.generate_response(user_input))
        except Exception as e:
            logger.error(f"❌ Error in sync wrapper: {e}")
            return asyncio.run(self._generate_smart_fallback_response(user_input))

    def extract_code_block(self, text: str) -> str:
        """Extract code block from markdown-style text"""
        if "```" not in text:
            return ""

        lines = text.split("\n")
        code_lines = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    break  # End of code block
                else:
                    in_code_block = True  # Start of code block
                    continue
            elif in_code_block:
                code_lines.append(line)

        return "\n".join(code_lines).strip() if code_lines else ""

    def extract_filename_guess(self, text: str, user_input: str = "") -> str:
        """Extract or guess filename from response text or user input"""
        combined_text = (text + " " + user_input).lower()

        # Look for explicit .aether or .py filenames
        words = combined_text.split()
        for word in words:
            if word.endswith(".aether") or word.endswith(".py"):
                # Clean up the word (remove punctuation)
                filename = word.strip(".,!?;:\"'")
                if filename.endswith((".aether", ".py")):
                    return filename

        # Look for plugin name patterns and create filename
        plugin_indicators = ["plugin", "create", "generate", "build", "make"]
        for indicator in plugin_indicators:
            if indicator in combined_text:
                # Extract potential plugin name
                words = combined_text.replace(indicator, "").strip().split()
                for word in words[:3]:  # Check first few words
                    if len(word) > 2 and word.isalpha():
                        return f"{word}_plugin.aether"

        return "generated_plugin.aether"

    def handle_llm_response(self, text: str, user_input: str = "") -> str:
        """
        Handle LLM response and check for code injection triggers

        Args:
            text: The LLM response text
            user_input: The original user input for context

        Returns:
            str: The potentially modified response text
        """
        # Check for code injection triggers
        text_lower = text.lower()

        # Pattern 1: Explicit plugin creation intent
        plugin_creation_patterns = [
            "plugin editor",
            "inject code",
            "created plugin",
            "generated plugin",
            "plugin code",
        ]

        # Pattern 2: Code blocks present
        has_code_block = "```" in text

        # Pattern 3: Plugin-related keywords
        plugin_keywords = any(
            pattern in text_lower for pattern in plugin_creation_patterns
        )

        # Only trigger injection if we have both intent and code
        if has_code_block and plugin_keywords:
            plugin_code = self.extract_code_block(text)

            if plugin_code and len(plugin_code.strip()) > 10:  # Valid code content
                filename = self.extract_filename_guess(text, user_input)

                # Attempt GUI injection
                if self.gui_interface and hasattr(
                    self.gui_interface, "inject_plugin_code"
                ):
                    try:
                        success = self.gui_interface.inject_plugin_code(
                            plugin_code, filename
                        )

                        if success:
                            logger.info(f"🎯 Code injection successful: {filename}")

                            # Store in memory if available (optional)
                            try:
                                # This could be enhanced with actual memory storage
                                pass
                            except Exception as e:
                                logger.debug(
                                    f"Could not store plugin creation in memory: {e}"
                                )

                            # Add injection confirmation to response
                            injection_note = f"\n\n🎯 **Plugin Editor Updated**: I've injected the {filename} code into your Plugin Editor tab! You can now review, edit, save, and test the plugin."
                            return text + injection_note
                        else:
                            logger.warning("⚠️ Code injection failed")
                    except Exception as e:
                        logger.error(f"❌ Code injection error: {e}")
                else:
                    logger.debug("⚠️ No GUI interface available for code injection")

        return text  # No injection triggered, return original text

    # ====================
    # SELF-IMPROVEMENT INTEGRATION
    # ====================

    def enable_self_improvement_monitoring(self, check_interval_hours: int = 24):
        """Enable automatic plugin improvement monitoring"""
        try:
            from .self_improvement_trigger import SelfImprovementScheduler

            if not hasattr(self, "improvement_scheduler"):
                self.improvement_scheduler = SelfImprovementScheduler(
                    workspace_path=self.workspace_path, gui_interface=self.gui_interface
                )
                self.improvement_scheduler.set_check_interval(check_interval_hours)
                self.improvement_scheduler.start_background_monitoring()
                logger.info(
                    f"🤖 Self-improvement monitoring enabled (every {check_interval_hours}h)"
                )
            else:
                logger.info("🤖 Self-improvement monitoring already active")

        except ImportError:
            logger.warning("⚠️ Self-improvement components not available")

    def disable_self_improvement_monitoring(self):
        """Disable automatic plugin improvement monitoring"""
        if hasattr(self, "improvement_scheduler"):
            self.improvement_scheduler.stop_background_monitoring()
            logger.info("⏹️ Self-improvement monitoring disabled")

    async def suggest_plugin_improvements(self, user_context: str = "") -> str:
        """Generate plugin improvement suggestions based on current context"""
        try:
            from .plugin_diff_engine import PluginDiffEngine

            # Initialize diff engine if not already done
            if not hasattr(self, "diff_engine"):
                self.diff_engine = PluginDiffEngine(self.workspace_path)

            # Analyze plugins for improvements
            proposals = await self.diff_engine.generate_improvement_proposals()

            if not proposals:
                return "✅ All your plugins look great! No improvement suggestions at this time."

            # Create natural response about improvements
            response_parts = ["🔧 I found some potential plugin improvements:\n"]

            for i, proposal in enumerate(proposals[:3], 1):  # Show top 3
                response_parts.append(f"""
{i}. **{proposal.plugin_id}**
   - Improvement: {proposal.proposed_change}
   - Impact: {proposal.impact}
   - Risk Level: {proposal.risk_level}
   - Confidence: {proposal.confidence:.1%}
""")

            if len(proposals) > 3:
                response_parts.append(
                    f"\n💡 Plus {len(proposals) - 3} more improvement opportunities!"
                )

            response_parts.append(
                "\nWould you like me to load any of these improvements into the Plugin Editor for review?"
            )

            return "".join(response_parts)

        except Exception as e:
            logger.error(f"❌ Failed to generate improvement suggestions: {e}")
            return "⚠️ I encountered an issue while analyzing plugins for improvements. Please try again later."

    async def auto_check_for_improvements(self) -> bool:
        """Automatically check for and suggest improvements (called by scheduler)"""
        try:
            suggestions = await self.suggest_plugin_improvements()

            # If improvements are found, they would be processed by the scheduler
            # This method is mainly for integration with the automatic system
            if "I found some potential" in suggestions:
                logger.info("🔍 Auto-check found improvement opportunities")
                return True
            else:
                logger.info("✅ Auto-check: No improvements needed")
                return False

        except Exception as e:
            logger.error(f"❌ Auto-check for improvements failed: {e}")
            return False

    # ====================
    # PLUGIN EDITOR INTEGRATION
    # ====================

    async def _handle_plugin_editor_intent(self, user_input: str) -> tuple[bool, str]:
        """
        🎯 Handle plugin editor intents and route to appropriate actions
        Returns: (intent_detected, response_message)
        """
        try:
            # Check if this is a plugin editor related intent
            text = user_input.lower()
            plugin_keywords = ["plugin", "editor"]
            action_keywords = ["load", "create", "generate", "inject", "populate", "fill", "open", "show"]

            # Must have at least one plugin keyword and one action keyword
            has_plugin_keyword = any(keyword in text for keyword in plugin_keywords)
            has_action_keyword = any(keyword in text for keyword in action_keywords)

            if not (has_plugin_keyword and has_action_keyword):
                return False, ""

            # Detect intent confidence
            keyword_count = sum(1 for keyword in plugin_keywords + action_keywords if keyword in text)
            confidence = min(0.5 + (keyword_count * 0.1), 0.9)

            # Route to plugin editor controller if available
            if self.plugin_editor_controller:
                success, response, action_data = self.plugin_editor_controller.handle_plugin_editor_intent(
                    user_input=user_input,
                    detected_intent="plugin_editor_action",
                    meta_reasoning_engine=self.meta_reasoning_engine
                )

                # Add conversation to history
                self.add_to_conversation_history("user", user_input)
                self.add_to_conversation_history("assistant", response)

                return True, response

            # Fallback if no controller available
            else:
                fallback_response = self._generate_plugin_editor_fallback(user_input, confidence)

                # Add to history
                self.add_to_conversation_history("user", user_input)
                self.add_to_conversation_history("assistant", fallback_response)

                return True, fallback_response

        except Exception as e:
            logger.error(f"❌ Plugin editor intent handling failed: {e}")
            return False, ""

    def _generate_plugin_editor_fallback(self, user_input: str, confidence: float) -> str:
        """Generate fallback response for plugin editor intents when controller unavailable"""
        text = user_input.lower()

        if "load" in text and "plugin" in text:
            return """🎯 I understand you want me to load a plugin into the editor! However, I don't currently have access to the Plugin Editor interface.

To load a plugin manually:
1. Click on the "Plugin Editor" tab
2. Use "Open Plugin File" to browse and load your plugin
3. The plugin code will appear in the editor for review and editing

Would you like me to help you with something else regarding plugins?"""

        elif any(word in text for word in ["create", "generate", "make"]) and "plugin" in text:
            return """🔧 I'd love to help you create a plugin! While I can't directly inject code into the Plugin Editor right now, I can help you in other ways:

**Plugin Creation Options:**
1. **Manual Creation**: I can provide you with plugin templates and code examples
2. **Code Generation**: I can generate plugin code that you can copy into the editor
3. **Step-by-Step Guide**: I can walk you through the plugin creation process

What type of plugin would you like to create? (e.g., assistant trainer, data processor, automation tool)"""

        elif "inject" in text or "populate" in text:
            return """📝 I understand you want me to populate the Plugin Editor with code! This feature requires direct GUI integration which isn't currently available.

**Alternative approaches:**
1. I can generate the plugin code and you can copy it into the editor
2. I can save the code to a file that you can open in the editor
3. I can provide step-by-step instructions for manual code entry

Would you like me to generate some plugin code for you to use?"""

        else:
            return f"""🎯 I detected that you want to work with the Plugin Editor (confidence: {confidence:.1%})!

While I can't directly control the Plugin Editor interface right now, I can:
• Generate plugin code and templates
• Explain plugin development concepts
• Help you plan plugin functionality
• Provide coding assistance and debugging

What specific plugin-related task can I help you with?"""

    # ====================
    # ENHANCED INTENT ROUTING WITH META-REASONING
    # ====================

    def _classify_user_intent(self, user_input: str) -> dict:
        """
        🧠 Classify user intent with meta-reasoning tracking
        """
        text = user_input.lower()

        # Plugin Editor Intent
        if any(word in text for word in ["plugin", "editor"]) and any(word in text for word in ["load", "create", "inject", "open"]):
            intent_data = {
                "category": "plugin_editor",
                "confidence": 0.8,
                "keywords": ["plugin", "editor"],
                "actions": ["load", "create", "inject", "open"]
            }
        # System Status Intent
        elif any(word in text for word in ["status", "health", "running", "working"]):
            intent_data = {
                "category": "system_status",
                "confidence": 0.7,
                "keywords": ["status", "system"],
                "actions": ["check", "monitor"]
            }
        # General Conversation
        else:
            intent_data = {
                "category": "general_conversation",
                "confidence": 0.5,
                "keywords": [],
                "actions": ["respond"]
            }

        # Track intent classification with meta-reasoning
        if self.meta_reasoning_engine:
            try:
                self.meta_reasoning_engine.explain_intent_routing(
                    user_input=user_input,
                    detected_intent=intent_data["category"],
                    confidence=intent_data["confidence"],
                    routing_decision=f"route_to_{intent_data['category']}",
                    available_routes=["plugin_editor", "system_status", "general_conversation", "fallback"],
                    reasoning=f"Detected keywords: {intent_data['keywords']}, Actions: {intent_data['actions']}"
                )
            except Exception as e:
                logger.debug(f"Meta-reasoning intent tracking failed: {e}")

        return intent_data
