/**
 * Persian UI strings (single source for user-facing copy, per DESIGN.md §8).
 *
 * Technical identifiers (OTP, JWT, API) stay in Latin script.
 */
export const strings = {
  appName: "ترب",
  login: "ورود",
  phoneNumber: "شماره موبایل",
  phonePlaceholder: "09123456789",
  sendCode: "ارسال کد",
  enterCode: "کد ارسال شده به پیامک را وارد کنید",
  codeIncorrect: "کد نادرست است",
  moreDisplay: "نمایش بیشتر",
  timeRemaining: "زمان باقیمانده",
  requestNewCode: "کد جدید درخواست کنید",
  loginButton: "ورود",
  pleaseLogin: "برای ادامه وارد شوید.",
  genericError: "خطایی رخ داد. دوباره تلاش کنید.",
  heroTitle: "مقایسه پلن های میزبانی و سرور در میان صدها ارائه دهنده",
  heroSubtitle:
    "پلن های میزبانی و سرور را یک جا جست و جو و مقایسه کنید.",
  comparePlans: "مقایسه پلن ها",
  howItWorks: "چگونه کار می کند",
  stepDevelop: "توسعه",
  stepDevelopTitle: "اتصال داده",
  stepDevelopBody: "ارائه دهندگان داده های پلن خود را به سیستم متصل می کنند.",
  stepPreview: "پیش نمایش",
  stepPreviewTitle: "جست و جو و فیلتر",
  stepPreviewBody: "پلنها را بر اساس قیمت، منطقه و مشخصات محدود کنید.",
  stepShip: "انتشار",
  stepShipTitle: "مقایسه و انتخاب",
  stepShipBody: "پلنها را کنار هم مقایسه کنید و بهترین گزینه را انتخاب کنید.",
  builtForScale: "ساختهشده برای مقیاس",
  badgeThroughput: "۱۰۰ درخواست بر ثانیه",
  badgeFreshness: "تازگی ۵ دقیقهای",
  badgeLocalIndex: "ایندکس محلی",

  // Company panel (spec 002)
  companyPanel: "پنل شرکت",
  registerNewCompany: "ثبت شرکت جدید",
  noCompanies: "هنوز شرکتی ثبت نکردهاید.",
  continueRegistration: "ادامه ثبت شرکت",
  switchCompany: "تغییر شرکت",
  unverifiedFlag: "تأییدنشده",
  verifiedStatus: "تأییدشده",
  pendingStatus: "در انتظار تأیید",
  rejectedStatus: "ردشده",
  stepCompanyInfo: "اطلاعات شرکت",
  stepVerification: "تأیید",
  stepDone: "انجامشده",
  stepPending: "در انتظار",
  stepLocked: "قفلشده",
  goToCurrentStep: "رفتن به مرحله فعلی",
  companyDomain: "دامنه شرکت",
  companyName: "نام شرکت",
  representativeName: "نام نماینده",
  companyPhone: "تلفن شرکت",
  internalNumber: "شماره داخلی (اختیاری)",
  submitCompany: "ثبت شرکت",
  panelBlockedVerified: "شرکت باید تأیید شده باشد.",
  panelBlockedCharged: "حساب شرکت باید شارژ شده باشد.",
  panelBlockedBoth: "شرکت باید تأیید شده و حساب آن شارژ شده باشد.",
  fullPanel: "پنل کامل شرکت",

  // Site chrome & main page (PAGES.yaml)
  brandTagline: "مقایسه پلن های میزبانی و سرور",
  navMainPage: "صفحه اصلی",
  navCompanies: "شرکت ها",
  navAboutUs: "درباره ما",
  menuOpen: "باز کردن منو",
  menuClose: "بستن منو",
  searchTitle: "جست و جوی شرکت ها و سرویس ها",
  searchPlaceholder: "نام شرکت یا پلن را وارد کنید",
  searchSubmit: "جست و جو",
  serviceTypeLabel: "نوع سرویس",
  serviceHost: "هاست",
  serviceVirtualServer: "سرور مجازی",
  serviceDedicatedServer: "سرور اختصاصی",
  serviceCdn: "CDN",
  filtersLabel: "فیلترها",
  serverLocationLabel: "موقعیت سرور",
  resourceLabel: "مشخصات منابع",
  resourceRam: "رم",
  resourceCpu: "پردازنده",
  resourceDisk: "فضای ذخیره سازی",
  resourceTraffic: "ترافیک",
  priceRangeLabel: "محدوده قیمت",
  priceFrom: "از",
  priceTo: "تا",
  priceAny: "هر قیمتی",
  priceRangeApply: "اعمال",
  priceRangeClear: "پاک کردن",
  clearFilters: "پاک کردن فیلترها",
  filtersTitle: "فیلترها",
  anyOption: "همه",
  resultsTitle: "نتایج",
  resultsPending: "جست و جو و فیلترها آماده است؛ نمایش نتایج به زودی فعال می شود.",
  resultsEmptyTitle: "هنوز چیزی برای نمایش نیست",
  noResults: "نتیجه ای پیدا نشد.",
  companyType: "شرکت",
  planType: "پلن",
  companyCardFallback: "توضیحات این شرکت به زودی منتشر می شود.",

  // Homepage sections (PAGES.yaml main page)
  ctaViewCompanies: "شرکت ها",
  ctaViewHosts: " بازدید از سرور ها و هاست ها",
  aboutTorbTitle: "ترب هاست چیست؟",
  aboutTorbBody:
    "ترب هاست یک موتور جست و جو و مقایسه پلن های میزبانی و سرور است. ارائه دهندگان داده های پلن خود را به سیستم متصل می کنند و شما در یک جا قیمت، منابع و موقعیت سرور صدها پلن را می بینید و بهترین گزینه را انتخاب می کنید.",
  aboutTorbPoint1Title: "داده های متصل از ارائه دهندگان",
  aboutTorbPoint1Body: "قیمت و مشخصات پلن ها مستقیم از ارائه دهندگان دریافت و به روز می شود.",
  aboutTorbPoint2Title: "مقایسه شفاف",
  aboutTorbPoint2Body: "پلن ها را بر اساس قیمت، منابع و موقعیت سرور کنار هم بگذارید.",
  aboutTorbPoint3Title: "خرید بدون واسطه",
  aboutTorbPoint3Body: "انتخاب و خرید را مستقیم با ارائه دهنده نهایی می کنید.",
  aboutTorbPoint4Title: "رایگان و بدون ثبت‌نام",
  aboutTorbPoint4Body: "همه‌ی پلن‌ها و مقایسه‌ها بدون نیاز به حساب کاربری در دسترس است.",

  howItWorksTitle: "مراحل کار با سایت",
  howItWorksIntro: "در سه گام ساده پلن مناسب خود را پیدا کنید.",

  rankingTitle: "معیارهای رتبه بندی",
  rankingIntro:
    "رتبه بندی شرکت ها و هاست ها بر پایه معیارهای زیر و به صورت شفاف محاسبه می شود.",
  rankingScoreLabel: "امتیاز",

  topHostsTitle: "برترین هاست ها",
  topHostsIntro: "هاست هایی با بالاترین رتبه بر اساس معیارهای رتبه بندی.",
  topHostsLocationLabel: "موقعیت",

  recentlyApprovedTitle: "تازه تأییدشده ها",
  recentlyApprovedIntro: "شرکت ها و هاست هایی که به تازگی تأیید یا به سیستم اضافه شده اند.",

  revenueTitle: "مدل درآمدی",
  revenueIntro:
    "استفاده از ترب هاست برای کاربران رایگان است و هزینه های پلتفرم از این راه ها تأمین می شود.",
  revenueNote: "نمایش ویژه هرگز معیارهای رتبه بندی را تغییر نمی دهد.",

  faqTitle: "پرسش های متداول",
  faqIntro: "پاسخ پرسش های پرتکرار درباره جست و جو، مقایسه و ثبت شرکت.",

  footerAbout: "ترب هاست؛ موتور جست و جو و مقایسه پلن های میزبانی و سرور.",
  footerLinksTitle: "دسترسی سریع",
  footerLegalTitle: "اطلاعات حقوقی",
  footerContactTitle: "تماس با ما",
  footerSocialTitle: "شبکه های اجتماعی",
  footerPrivacy: "حریم خصوصی",
  footerTerms: "شرایط استفاده",
  footerEmail: "support@torobhost.ir",
  footerPhone: "۰۲۱-۱۲۳۴۵۶۷۸",
  footerAddress: "تهران، ایران",
  footerSocialInstagram: "اینستاگرام",
  footerSocialTelegram: "تلگرام",
  footerSocialLinkedin: "لینکدین",
  footerSocialGithub: "گیت هاب",
  footerCopyright: "ترب هاست. همه حقوق محفوظ است.",
} as const;

/** Three-step "how it works" pipeline; tones form the olive ramp from DESIGN.md §4. */
export const howItWorksSteps = [
  {
    index: "۱",
    label: strings.stepDevelop,
    title: strings.stepDevelopTitle,
    body: strings.stepDevelopBody,
    tone: "var(--ds-olive-500)",
  },
  {
    index: "۲",
    label: strings.stepPreview,
    title: strings.stepPreviewTitle,
    body: strings.stepPreviewBody,
    tone: "var(--ds-olive-700)",
  },
  {
    index: "۳",
    label: strings.stepShip,
    title: strings.stepShipTitle,
    body: strings.stepShipBody,
    tone: "var(--ds-olive-800)",
  },
] as const;

/** Transparent ranking criteria: what is measured and how (homepage "ranking criteria"). */
export const rankingCriteria = [
  {
    title: "قیمت",
    body: "هزینه ماهانه و نسبت قیمت به منابع در مقایسه با پلن های مشابه.",
  },
  {
    title: "کارایی و منابع",
    body: "مقدار رم، پردازنده، فضای ذخیره سازی و ترافیک هر پلن.",
  },
  {
    title: "پایداری و آپ تایم",
    body: "سابقه آپ تایم و نرخ خطای گزارش شده سرویس.",
  },
  {
    title: "کیفیت پشتیبانی",
    body: "سرعت پاسخ گویی و رضایت کاربران از پشتیبانی.",
  },
  {
    title: "تازگی داده ها",
    body: "تغییرات قیمت و مشخصات حداکثر تا پنج دقیقه در نتایج اعمال می شود.",
  },
] as const;

/** Highest-ranked hosts highlighted on the homepage. Mock until the ranking API lands. */
export const topHosts = [
  {
    rank: "۱",
    name: "میزبان سرور پارس",
    domain: "pars-host.ir",
    score: "۹۴",
    location: "تهران",
    service: strings.serviceHost,
  },
  {
    rank: "۲",
    name: "ابر رایان",
    domain: "abrrrayan.ir",
    score: "۹۱",
    location: "فرانکفورت",
    service: strings.serviceVirtualServer,
  },
  {
    rank: "۳",
    name: "داده گستر",
    domain: "dadehgostar.ir",
    score: "۸۸",
    location: "مشهد",
    service: strings.serviceDedicatedServer,
  },
  {
    rank: "۴",
    name: "شبکه افرا",
    domain: "afra-cdn.ir",
    score: "۸۵",
    location: "ایران",
    service: strings.serviceCdn,
  },
] as const;

/** Recently verified providers; mock until the approval feed is served by the API. */
export const recentlyApproved = [
  { name: "هاست ایرانیان", logo: "https://www.arvancloud.ir/favicon.ico", domain: "iranhost.ir", service: strings.serviceHost, time: "۲۴ ساعت پیش" },
  {
    name: "سرور آسیا",
    logo: "https://www.arvancloud.ir/favicon.ico",
    domain: "asia-server.ir",
    service: strings.serviceVirtualServer,
    time: "۲ روز پیش",
  },
  {
    name: "ابریار",
    domain: "abriyar.ir",
    logo: "https://www.arvancloud.ir/favicon.ico",
    service: strings.serviceDedicatedServer,
    time: "۳ روز پیش",
  },
] as const;

/** How the platform earns money, stated plainly (homepage "revenue model"). */
export const revenueItems = [
  {
    title: "کمیسیون فروش",
    body: "درصدی از فروشی که از طریق لینک های ترب هاست انجام می شود.",
  },
  {
    title: "نمایش ویژه",
    body: "جایگاه ویژه برای ارائه دهندگانی که می خواهند بیشتر دیده شوند.",
  },
  {
    title: "تبلیغات",
    body: "تبلیغات هدفمند مرتبط با میزبانی و سرور، همیشه با برچسب مشخص.",
  },
] as const;

/** Frequently asked questions, rendered as the homepage FAQ accordion. */
export const faqItems = [
  {
    question: "چگونه پلن مناسب را پیدا کنم؟",
    answer:
      "با جست و جوی نام شرکت یا سرویس و اعمال فیلترهای قیمت، منابع و موقعیت سرور، فهرست پلن ها را محدود کنید و آن ها را کنار هم مقایسه کنید.",
  },
  {
    question: "تفاوت هاست، سرور مجازی و سرور اختصاصی چیست؟",
    answer:
      "هاست برای سایت های کوچک با ترافیک محدود مناسب است، سرور مجازی منابع اختصاصی تر و کنترل بیشتری می دهد و سرور اختصاصی تمام منابع یک ماشین را در اختیار شما می گذارد.",
  },
  {
    question: "داده های پلن ها و قیمت ها چقدر به روز است؟",
    answer:
      "ارائه دهندگان داده های خود را به سیستم متصل می کنند و تغییرات قیمت حداکثر تا پنج دقیقه در نتایج جست و جو اعمال می شود.",
  },
  {
    question: "رتبه بندی شرکت ها بر چه اساسی است؟",
    answer:
      "رتبه بندی بر پایه قیمت، کارایی و منابع، پایداری و آپ تایم، کیفیت پشتیبانی و تازگی داده ها محاسبه می شود؛ جزئیات در بخش معیارهای رتبه بندی آمده است.",
  },
  {
    question: "چگونه شرکت خود را ثبت کنم؟",
    answer:
      "از مسیر پنل شرکت، اطلاعات شرکت و دامنه را ثبت کنید و پس از تأیید، داده های پلن های خود را به سیستم متصل کنید.",
  },
  {
    question: "استفاده از ترب هاست هزینه ای دارد؟",
    answer:
      "جست و جو و مقایسه برای کاربران رایگان است؛ مدل درآمدی ما در بخش مدل درآمدی توضیح داده شده است.",
  },
] as const;

/** Footer navigation columns; the contact and social columns are rendered inline. */
export const footerLinkGroups = [
  {
    title: strings.footerLinksTitle,
    links: [
      { label: strings.navMainPage, href: "/" },
      { label: strings.navCompanies, href: "/companies" },
      { label: strings.navAboutUs, href: "/about" },
    ],
  },
  {
    title: strings.footerLegalTitle,
    links: [
      { label: strings.footerPrivacy, href: "/about" },
      { label: strings.footerTerms, href: "/about" },
    ],
  },
] as const;
