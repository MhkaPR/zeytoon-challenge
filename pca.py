import numpy as np
titles = [
    # --- سری پایه / اقتصادی ---
    "سرور مجازی پایه",
    "سرور مجازی اقتصادی",
    "سرور مجازی استارتر",
    "سرور مجازی مقرون‌به‌صرفه",
    "سرور مجازی مبتدی",
    "هاستینگ پایه",
    "هاستینگ اقتصادی",
    "هاستینگ استارتر",

    # --- سری حرفه‌ای ---
    "سرور مجازی حرفه‌ای",
    "سرور مجازی پرو",
    "سرور مجازی پلاس",
    "سرور مجازی پریمیوم",
    "هاستینگ حرفه‌ای",
    "هاستینگ پرو",
    "هاستینگ پریمیوم",

    # --- سری سازمانی ---
    "سرور اختصاصی سازمانی",
    "سرور اختصاصی اینترپرایز",
    "سرور ابری سازمانی",
    "سرور ابری اینترپرایز",
    "سرور اختصاصی ویژه شرکت‌ها",

    # --- سری گیمینگ ---
    "سرور مجازی گیمینگ",
    "سرور اختصاصی گیمینگ",
    "سرور ماینکرفت",
    "سرور گیم کانتر",
    "سرور مجازی مخصوص بازی",

    # --- سری گرافیکی و هوش مصنوعی ---
    "سرور GPU هوش مصنوعی",
    "سرور گرافیکی رندر",
    "سرور اختصاصی GPU",
    "سرور یادگیری ماشین",

    # --- سری ابری ---
    "سرور ابری انعطاف‌پذیر",
    "سرور ابری مقیاس‌پذیر",
    "سرور ابری پایه",
    "کلود سرور حرفه‌ای",

    # --- سری مخصوص (ذخیره‌سازی، ایمیل، وردپرس) ---
    "سرور ذخیره‌سازی بک‌آپ",
    "سرور فایل و ذخیره‌سازی",
    "سرور ایمیل اختصاصی",
    "هاستینگ وردپرس سریع",
    "هاستینگ وردپرس حرفه‌ای",
    "سرور فروشگاهی",
    "سرور وی‌پی‌ان",
]

def clean(t):
    return t

from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.decomposition import PCA

hv = HashingVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                       n_features=2**10, alternate_sign=False, norm="l2")
X = hv.transform(titles)          # sparse
X_dense = X.toarray()
cleaned = [clean(t) for t in titles]
X = hv.transform(cleaned).toarray()

pca = PCA(n_components=4, random_state=0).fit(X)
print("variance: ", pca.explained_variance_ratio_.round(3))

Z = pca.transform(X_dense)        # shape: (n_titles, 4)

for k in range(4):
    scores = Z[:, k]
    print(f"\n{'='*60}\nPC{k+1}  (var={pca.explained_variance_ratio_[k]:.3f})")
    order = np.argsort(-np.abs(scores))   # مرتب‌سازی بر اساس قدرمطلق امتیاز
    for i in order[:8]:
        sign = "+" if scores[i] >= 0 else "-"
        print(f"  {scores[i]:+.3f}  {titles[i]}")