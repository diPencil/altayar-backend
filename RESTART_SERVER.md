# 🔄 إعادة تشغيل الـ Server

## الخطوات:

### 1. أوقف الـ Server الحالي
في terminal الـ backend، اضغط:
```
Ctrl + C
```

### 2. شغل الـ Server تاني
```bash
python server.py
```

### 3. اختبر Fawaterk API
في terminal جديد:
```bash
python test_fawaterk.py
```

**النتيجة المتوقعة:**
```
✅ SUCCESS!
Invoice ID: xxx
Payment URL: https://app.fawaterk.com/pay/xxx
```

---

## إذا نجح الاختبار:
✅ Fawaterk شغال!
✅ نبدأ نعمل Frontend

## إذا فشل الاختبار:
❌ راجع المفاتيح
❌ تأكد من الـ API Key صحيح
