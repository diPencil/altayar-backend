import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from modules.chat.models import Conversation, Message, MessageType, ConversationStatus
import logging
import re

logger = logging.getLogger(__name__)

class BotService:
    """
    Simple rule-based chatbot service.
    """
    
    WELCOME_MESSAGE = (
        "مرحباً بك في الطيار VIP! 👋\n"
        "أنا المساعد الآلي. كيف يمكنني مساعدتك اليوم؟\n\n"
        "1️⃣ استفسار عن الحجوزات\n"
        "2️⃣ أسعار الخدمات\n"
        "3️⃣ التحدث مع خدمة العملاء"
    )
    
    BOOKING_REPLY = (
        "يمكنك متابعة حجوزاتك الحالية أو السابقة من خلال قسم 'حجوزاتي' في القائمة السفلية للتطبيق.\n"
        "هل لديك استفسار آخر؟"
    )
    
    PRICING_REPLY = (
        "تختلف الأسعار حسب الخدمات والعروض المتاحة حالياً.\n"
        "يرجى زيارة قسم 'العروض' لمعرفة أحدث باقاتنا الحصرية."
    )
    
    HANDOVER_MESSAGE = (
        "جاري تحويلك إلى أحد ممثلي خدمة العملاء... ⏳\n"
        "يرجى الانتظار، وسيقوم أحد الموظفين بالرد عليك في أقرب وقت."
    )

    MEMBERSHIP_SUBSCRIBE_REPLY_AR = (
        "تم استلام طلب اشتراكك في {{plan}} ✅\n"
        "فريق الدعم هيرد عليك خلال ثوانٍ.\n\n"
        "ولو تحب تسرّع العملية: ابعت رقم الهاتف والمدينة."
    )

    MEMBERSHIP_SUBSCRIBE_REPLY_EN = (
        "We received your subscription request for {{plan}} ✅\n"
        "Support will reply within seconds.\n\n"
        "To speed things up, please send your phone number and city."
    )

    OFFER_BOOKING_REPLY_AR = (
        "تم استلام طلبك بخصوص العرض ✅\n"
        "📌 {{offer}}\n"
        "💰 السعر: {{price}}\n\n"
        "فريق الدعم هيرد عليك خلال ثوانٍ.\n"
        "ولو تحب تسرّع العملية: ابعت رقم الهاتف والمدينة."
    )

    OFFER_BOOKING_REPLY_EN = (
        "We received your offer request ✅\n"
        "📌 {{offer}}\n"
        "💰 Price: {{price}}\n\n"
        "Support will reply within seconds.\n"
        "To speed things up, please send your phone number and city."
    )

    @staticmethod
    def _contains_arabic(text: str) -> bool:
        if not text:
            return False
        return re.search(r"[\u0600-\u06FF]", text) is not None

    @staticmethod
    def _extract_plan_label_from_subscription_message(text: str) -> str | None:
        """
        Try to extract plan label like: 'Gold (GM)' from messages such as:
        - Hello Altayar, I want to subscribe to Gold (GM).
        - مرحباً الطيار، أريد الاشتراك في الذهبية (GM).
        """
        if not text:
            return None

        s = text.strip()

        # Prefer extracting "(CODE)" part
        m_code = re.search(r"\(([^)]+)\)", s)
        code = m_code.group(1).strip() if m_code else None

        # Try to extract plan name before "(CODE)"
        plan_name = None
        if m_code:
            before = s[: m_code.start()].strip()
            # English pattern
            m_en = re.search(r"subscribe to\s+(.+)$", before, flags=re.IGNORECASE)
            if m_en:
                plan_name = m_en.group(1).strip(" .،")
            else:
                # Arabic pattern
                m_ar = re.search(r"الاشتراك\s+في\s+(.+)$", before)
                if m_ar:
                    plan_name = m_ar.group(1).strip(" .،")

        # If we got at least code, return combined label
        if plan_name and code:
            return f"{plan_name} ({code})"
        if code and not plan_name:
            return f"({code})"
        return None

    @staticmethod
    def _is_membership_subscription_intent(text: str) -> bool:
        if not text:
            return False
        s = text.strip()
        if re.search(r"\bsubscribe to\b", s, flags=re.IGNORECASE):
            return True
        if "أريد الاشتراك" in s or "الاشتراك" in s:
            return True
        return False

    @staticmethod
    def _is_offer_booking_intent(text: str) -> bool:
        """
        Detect messages coming from the app "Contact us" on offer checkout.
        Examples:
          - Hello Altayar, I want to book this offer: X. Price: 100 USD.
          - مرحباً الطيار، أريد حجز هذا العرض: X. السعر: 100 USD.
        """
        if not text:
            return False
        s = text.strip()
        if "أريد حجز هذا العرض" in s or "حجز هذا العرض" in s:
            return True
        if re.search(r"\bbook this offer\b", s, flags=re.IGNORECASE):
            return True
        return False

    @staticmethod
    def _extract_offer_title_and_price(text: str) -> tuple[str | None, str | None]:
        """
        Extract offer title and price string from the booking message.
        Returns: (offer_title, price_str)
        """
        if not text:
            return (None, None)
        s = text.strip()

        # Arabic: "... العرض: TITLE. السعر: PRICE CURRENCY"
        m_ar = re.search(r"العرض\s*:\s*(.*?)\s*\.?\s*السعر\s*:\s*([0-9][0-9,]*(?:\.[0-9]+)?\s*[A-Za-z]{3})", s)
        if m_ar:
            return (m_ar.group(1).strip(" .،"), m_ar.group(2).strip())

        # English: "... offer: TITLE. Price: PRICE CURRENCY"
        m_en = re.search(r"offer\s*:\s*(.*?)\s*\.?\s*price\s*:\s*([0-9][0-9,]*(?:\.[0-9]+)?\s*[A-Za-z]{3})", s, flags=re.IGNORECASE)
        if m_en:
            return (m_en.group(1).strip(" .,"), m_en.group(2).strip())

        return (None, None)
    
    @staticmethod
    def process_message(db: Session, conversation: Conversation, user_message: str):
        """
        Process user message and generate bot response or handover.
        """
        if not conversation.is_bot_active:
            return None

        reply_content = None
        should_handover = False
        
        msg = user_message.strip()

        # Membership subscription intent (from memberships-explore auto message)
        if BotService._is_membership_subscription_intent(msg):
            plan_label = BotService._extract_plan_label_from_subscription_message(msg) or ""
            is_ar = BotService._contains_arabic(msg)
            template = BotService.MEMBERSHIP_SUBSCRIBE_REPLY_AR if is_ar else BotService.MEMBERSHIP_SUBSCRIBE_REPLY_EN
            reply_content = template.replace("{{plan}}", plan_label or ("هذه العضوية" if is_ar else "this tier"))
            should_handover = True

        # Offer booking intent (from offer-checkout auto message)
        if not reply_content and BotService._is_offer_booking_intent(msg):
            is_ar = BotService._contains_arabic(msg)
            offer_title, price_str = BotService._extract_offer_title_and_price(msg)
            template = BotService.OFFER_BOOKING_REPLY_AR if is_ar else BotService.OFFER_BOOKING_REPLY_EN
            reply_content = template.replace("{{offer}}", offer_title or ("هذا العرض" if is_ar else "this offer"))
            reply_content = reply_content.replace("{{price}}", price_str or ("—" if is_ar else "—"))
            should_handover = True
        
        # Simple Logic
        if not reply_content and (msg == "1" or "حجز" in msg or "booking" in msg.lower()):
            reply_content = BotService.BOOKING_REPLY
            
        elif not reply_content and (msg == "2" or "سعر" in msg or "price" in msg.lower() or "cost" in msg.lower()):
            reply_content = BotService.PRICING_REPLY
            
        elif not reply_content and (msg == "3" or "دعم" in msg or "support" in msg.lower() or "help" in msg.lower() or "مساعدة" in msg):
            reply_content = BotService.HANDOVER_MESSAGE
            should_handover = True
            
        elif not reply_content:
            # Default fallback for unrecogsized input: re-state options
            reply_content = (
                "عذراً، لم أفهم طلبك.\n"
                "يرجى اختيار رقم من القائمة:\n\n"
                "1️⃣ استفسار عن الحجوزات\n"
                "2️⃣ أسعار الخدمات\n"
                "3️⃣ التحدث مع خدمة العملاء"
            )

        # Create Bot Message
        if reply_content:
            bot_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                sender_id=conversation.customer_id, # Or a dedicated bot user ID if available, using cust ID + SYSTEM role is okay-ish but better to allow null sender or dedicated system ID.
                # Actually models.py says sender_id is foreign key to users.id. 
                # We should use a system user or the customer ID but with specific role.
                # Let's inspect routes.py again. System messages use current_user.id.
                # A proper way is to have a BOT user in DB, but for now we might reuse customer_id but role='SYSTEM' or 'BOT'.
                # Wait, if we use customer_id it will show as customer sent it?
                # Frontend checks sender_role. So checking `sender_role == 'CUSTOMER'` determines alignment.
                # So we can use customer_id technically as long as role is BOT.
                sender_role="BOT", 
                message_type=MessageType.TEXT,
                content=reply_content,
                created_at=datetime.utcnow()
            )
            
            # Correction: sender_id must exist in users table. 
            # Ideally we have a 'system' user. If not, we can use the customer's ID but mark role as BOT?
            # Or better, let's check if there is an Admin ID we can use? 
            # For safety/simplicity in this codebase without creating new user seeds:
            # We will use the customer_id BUT role='BOT'. The frontend should render it based on role.
            
            db.add(bot_msg)
            
            conversation.last_message_at = datetime.utcnow()
            conversation.last_message_preview = reply_content[:100]
            conversation.customer_unread_count = (conversation.customer_unread_count or 0) + 1
            
            if should_handover:
                conversation.is_bot_active = False
                conversation.status = ConversationStatus.WAITING # Move to waiting for agents
            
            db.commit()
            db.refresh(bot_msg)
            return bot_msg
            
        return None

    @staticmethod
    def send_welcome_message(db: Session, conversation: Conversation):
        """
        Send initial welcome message.
        """
        # If the conversation started from a membership subscription request,
        # send a focused auto-reply instead of the generic menu.
        try:
            # last_message_preview is set to the user's first message on start
            initial_msg = (conversation.last_message_preview or "").strip()
        except Exception:
            initial_msg = ""

        welcome_content = BotService.WELCOME_MESSAGE
        should_handover = False

        if BotService._is_membership_subscription_intent(initial_msg):
            plan_label = BotService._extract_plan_label_from_subscription_message(initial_msg) or ""
            is_ar = BotService._contains_arabic(initial_msg)
            template = BotService.MEMBERSHIP_SUBSCRIBE_REPLY_AR if is_ar else BotService.MEMBERSHIP_SUBSCRIBE_REPLY_EN
            welcome_content = template.replace("{{plan}}", plan_label or ("هذه العضوية" if is_ar else "this tier"))
            should_handover = True
        elif BotService._is_offer_booking_intent(initial_msg):
            is_ar = BotService._contains_arabic(initial_msg)
            offer_title, price_str = BotService._extract_offer_title_and_price(initial_msg)
            template = BotService.OFFER_BOOKING_REPLY_AR if is_ar else BotService.OFFER_BOOKING_REPLY_EN
            welcome_content = template.replace("{{offer}}", offer_title or ("هذا العرض" if is_ar else "this offer"))
            welcome_content = welcome_content.replace("{{price}}", price_str or ("—" if is_ar else "—"))
            should_handover = True

        bot_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            sender_id=conversation.customer_id, 
            sender_role="BOT",
            message_type=MessageType.TEXT,
            content=welcome_content,
            created_at=datetime.utcnow()
        )
        
        db.add(bot_msg)
        conversation.last_message_at = datetime.utcnow()
        conversation.last_message_preview = welcome_content[:100]
        conversation.customer_unread_count = (conversation.customer_unread_count or 0) + 1

        if should_handover:
            conversation.is_bot_active = False
            # If unassigned, mark as waiting for agents. If assigned, keep status as-is.
            if conversation.status == ConversationStatus.OPEN:
                conversation.status = ConversationStatus.WAITING
        
        db.commit()
