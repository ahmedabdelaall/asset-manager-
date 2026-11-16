# Asset Master — نظام إدارة الأصول المؤسسي

**المشروع الرئيسي (Master)** — مصدر الحقيقة الوحيد. كل نسخة لأي شركة تُنشأ منه (`tools/make_deployment.py`)،
ولا تُعدَّل الأكواد داخل نسخ الشركات. بيانات كل شركة (قاعدة بيانات، ملفات، أسرار، إعدادات) تعيش خارج الكود في مجلد/وحدة تخزين خاصة بها.

## التشغيل السريع بـ Docker (بورت 5222)

```bash
docker compose up -d --build         # يبني ويشغّل التطبيق
docker compose logs assetmaster       # يعرض "رمز الإعداد" عند أول تشغيل
```

افتح `http://عنوان-السيرفر:5222` ← أدخل رمز الإعداد ← أنشئ الشركة والمدير ← فعّل الترخيص.

التفاصيل الكاملة: [`docs/DEPLOY_DOCKER.md`](docs/DEPLOY_DOCKER.md) · الترخيص: [`docs/LICENSING.md`](docs/LICENSING.md) · البنية: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## التشغيل بدون Docker (للتطوير)

```bash
pip install -r requirements.txt
AM_INSTANCE=./instances/default AM_PORT=5222 python -m core
```

## الاختبارات

```bash
cd tests && python -m unittest test_api test_tools -v
```

## هيكل المشروع

| المسار | الوظيفة |
|---|---|
| `core/` | كود المنتج (الخادم، الأمان، الصلاحيات، الترخيص، الواجهة) |
| `core/migrations/` | تغييرات قاعدة البيانات المرقّمة (لا تُعدَّل بعد صدورها) |
| `core/web/` | الواجهة (عربي/إنجليزي، فاتح/داكن) |
| `tools/` | أدوات الإدارة وإصدار التراخيص وتوليد نسخ الشركات |
| `tests/` | اختبارات آلية |
| `CHANGELOG.md` | ملاحظات كل إصدار |
