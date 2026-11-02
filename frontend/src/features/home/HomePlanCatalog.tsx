"use client";

import { Button, Checkbox, Label, Slider, Tabs, Typography } from "@heroui/react";
import { useMemo, useState } from "react";

import { strings } from "@/src/lib/i18n/strings";

type PlanType = "hosting" | "wordpress" | "vps" | "dedicated" | "cloud";

interface HomePlan {
  id: number;
  provider: string;
  name: string;
  type: PlanType;
  location: string;
  cpu: number;
  ram: number;
  disk: number;
  price: number;
  os: "linux" | "windows";
}

const PLANS: HomePlan[] = [
  { id: 1, provider: "لیارا", name: "سرور پایه", type: "vps", location: "ایران", cpu: 2, ram: 2, disk: 30, price: 320000, os: "linux" },
  { id: 2, provider: "ابرآروان", name: "سرور ابری", type: "vps", location: "ایران", cpu: 2, ram: 2, disk: 40, price: 380000, os: "linux" },
  { id: 3, provider: "پارس‌پک", name: "سرور اروپا", type: "vps", location: "آلمان", cpu: 2, ram: 4, disk: 50, price: 590000, os: "linux" },
  { id: 4, provider: "ایران‌سرور", name: "سرور حرفه‌ای", type: "vps", location: "ایران", cpu: 4, ram: 4, disk: 60, price: 690000, os: "windows" },
  { id: 5, provider: "ابرآروان", name: "سرور پرقدرت", type: "vps", location: "ایران", cpu: 4, ram: 8, disk: 80, price: 840000, os: "linux" },
  { id: 6, provider: "لیارا", name: "سرور اروپا", type: "vps", location: "آلمان", cpu: 8, ram: 16, disk: 100, price: 1190000, os: "linux" },
  { id: 7, provider: "پارس‌پک", name: "هاست لینوکس", type: "hosting", location: "ایران", cpu: 1, ram: 1, disk: 20, price: 180000, os: "linux" },
  { id: 8, provider: "ایران‌سرور", name: "هاست وردپرس", type: "wordpress", location: "ایران", cpu: 2, ram: 2, disk: 30, price: 260000, os: "linux" },
  { id: 9, provider: "لیارا", name: "سرور اختصاصی", type: "dedicated", location: "آلمان", cpu: 16, ram: 32, disk: 500, price: 1450000, os: "linux" },
  { id: 10, provider: "ابرآروان", name: "سرور ابری منعطف", type: "cloud", location: "ایران", cpu: 4, ram: 8, disk: 100, price: 980000, os: "linux" },
];

const PROVIDERS = ["لیارا", "ابرآروان", "پارس‌پک", "ایران‌سرور"];
const TYPES: { id: "all" | PlanType; label: string }[] = [
  { id: "all", label: "همه سرویس‌ها" },
  { id: "hosting", label: "هاست اشتراکی" },
  { id: "wordpress", label: "هاست وردپرس" },
  { id: "vps", label: "سرور مجازی" },
  { id: "dedicated", label: "سرور اختصاصی" },
  { id: "cloud", label: "سرور ابری" },
];

const formatPrice = (value: number) => value.toLocaleString("fa-IR");

export function HomePlanCatalog() {
  const [type, setType] = useState<string>("vps");
  const [providers, setProviders] = useState<string[]>([]);
  const [maxPrice, setMaxPrice] = useState(1500000);
  const [os, setOs] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [sort, setSort] = useState("default");

  const plans = useMemo(() => {
    const matching = PLANS.filter((plan) =>
      (type === "all" || plan.type === type) &&
      (!providers.length || providers.includes(plan.provider)) &&
      plan.price <= maxPrice &&
      (!os.length || os.includes(plan.os)) &&
      (!locations.length || locations.includes(plan.location)),
    );
    if (sort === "price") return matching.sort((left, right) => left.price - right.price);
    if (sort === "expensive") return matching.sort((left, right) => right.price - left.price);
    return matching;
  }, [locations, maxPrice, os, providers, sort, type]);

  function toggle(values: string[], value: string, update: (next: string[]) => void) {
    update(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  }

  function resetFilters() {
    setProviders([]);
    setMaxPrice(1500000);
    setOs([]);
    setLocations([]);
    setSort("default");
    setType("vps");
  }

  return (
    <section className="flex flex-col gap-[24px]" aria-labelledby="home-plans-title">
      <div className="flex flex-col items-start justify-between gap-[12px] sm:flex-row sm:items-end">
        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[22px] font-semibold sm:text-[25px]" id="home-plans-title" type="h2">
            قیمت‌ها را کنار هم ببینید.
          </Typography>
          <Typography color="muted" type="body-sm">
            منابع سخت‌افزاری، موقعیت جغرافیایی و امکانات را مقایسه کنید.
          </Typography>
        </div>
        <a className="text-[13px] font-semibold text-accent" href="/companies">
          مشاهده همه ارائه‌دهندگان ←
        </a>
      </div>

      <Tabs
        className="w-full"
        selectedKey={type}
        onSelectionChange={(key) => setType(String(key))}
        variant="secondary"
      >
        <Tabs.ListContainer className="bg-transparent">
          <Tabs.List aria-label="نوع سرویس" className="w-full justify-start overflow-x-auto">
            {TYPES.map((item) => (
              <Tabs.Tab className="shrink-0" id={item.id} key={item.id}>
                {item.label}
                <Tabs.Indicator />
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs.ListContainer>
        {TYPES.map((item) => (
          <Tabs.Panel className="hidden" id={item.id} key={item.id}>{" "}</Tabs.Panel>
        ))}
      </Tabs>

      <div className="grid gap-[24px] lg:grid-cols-[225px_minmax(0,1fr)] lg:gap-[32px]">
        <aside className="flex flex-col gap-[20px] rounded-[var(--radius)] border border-[var(--separator)] p-[16px] lg:rounded-none lg:border-0 lg:border-e lg:pe-[22px]">
          <div className="flex flex-col gap-[10px] border-b border-[var(--separator)] pb-[16px]">
            <Typography className="font-semibold" type="body-sm">فیلتر سرویس‌ها</Typography>
            {PROVIDERS.map((provider) => (
              <Checkbox
                isSelected={providers.includes(provider)}
                key={provider}
                onChange={() => toggle(providers, provider, setProviders)}
              >
                <Checkbox.Content>
                  <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                  {provider}
                </Checkbox.Content>
              </Checkbox>
            ))}
          </div>

          <div className="flex flex-col gap-[10px] border-b border-[var(--separator)] pb-[16px]">
            <Label className="font-semibold">محدوده هزینه ماهانه</Label>
            <Slider
              aria-label="حداکثر قیمت ماهانه"
              maxValue={1500000}
              minValue={300000}
              step={50000}
              value={maxPrice}
              onChange={(next) => typeof next === "number" && setMaxPrice(next)}
            >
              <Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track>
            </Slider>
            <Typography color="muted" type="body-xs">تا {formatPrice(maxPrice)} تومان</Typography>
          </div>

          <div className="flex flex-col gap-[10px] border-b border-[var(--separator)] pb-[16px]">
            <Typography className="font-semibold" type="body-sm">نوع سیستم‌عامل</Typography>
            {(["linux", "windows"] as const).map((value) => (
              <Checkbox
                isSelected={os.includes(value)}
                key={value}
                onChange={() => toggle(os, value, setOs)}
              >
                <Checkbox.Content>
                  <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                  {value === "linux" ? "لینوکس" : "ویندوز"}
                </Checkbox.Content>
              </Checkbox>
            ))}
          </div>

          <div className="flex flex-col gap-[10px]">
            <Typography className="font-semibold" type="body-sm">موقعیت سرور</Typography>
            {["ایران", "آلمان", "فنلاند"].map((location) => (
              <Checkbox
                isSelected={locations.includes(location)}
                key={location}
                onChange={() => toggle(locations, location, setLocations)}
              >
                <Checkbox.Content>
                  <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                  {location}
                </Checkbox.Content>
              </Checkbox>
            ))}
          </div>
        </aside>

        <div className="min-w-0">
          <div className="mb-[12px] flex items-center justify-between gap-[12px]">
            <Typography color="muted" type="body-xs">
              {plans.length.toLocaleString("fa-IR")} سرویس پیشنهادی
            </Typography>
            <label className="flex items-center gap-[8px] text-[12px] text-muted">
              مرتب‌سازی
              <select
                className="rounded-[var(--radius)] border border-[var(--separator)] bg-background px-[10px] py-[7px] text-foreground"
                value={sort}
                onChange={(event) => setSort(event.target.value)}
              >
                <option value="default">پیشنهاد میزبان‌یاب</option>
                <option value="price">ارزان‌ترین</option>
                <option value="expensive">گران‌ترین</option>
              </select>
            </label>
          </div>

          {plans.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[650px] border-collapse text-right">
                <thead>
                  <tr className="border-b border-[var(--separator)] text-[11px] text-muted">
                    {["ارائه‌دهنده / پلن", "پردازنده", "حافظه رم", "فضای ذخیره‌سازی", "قیمت ماهانه", "جزئیات"].map((heading) => (
                      <th className="px-[10px] py-[13px] font-normal" key={heading}>{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {plans.map((plan) => (
                    <tr className="border-b border-[var(--separator)] text-[12px]" key={plan.id}>
                      <td className="px-[10px] py-[15px]">
                        <strong className="block font-semibold">{plan.provider}</strong>
                        <span className="text-[11px] text-muted">{plan.name} · {plan.location}</span>
                      </td>
                      <td className="whitespace-nowrap px-[10px] py-[15px] text-muted">{plan.cpu.toLocaleString("fa-IR")} vCPU</td>
                      <td className="whitespace-nowrap px-[10px] py-[15px] text-muted">{plan.ram.toLocaleString("fa-IR")} GB RAM</td>
                      <td className="whitespace-nowrap px-[10px] py-[15px] text-muted">{plan.disk.toLocaleString("fa-IR")} GB SSD</td>
                      <td className="whitespace-nowrap px-[10px] py-[15px]">
                        <strong className="text-[15px] font-semibold">{formatPrice(plan.price)}</strong>
                        <span className="block text-[10px] text-muted">تومان / ماه</span>
                      </td>
                      <td className="px-[10px] py-[15px]">
                        <Button size="sm" variant="secondary">مشاهده پلن</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-[36px] text-center text-[13px] text-muted">سرویسی با این فیلترها پیدا نشد.</div>
          )}

          <div className="flex flex-col items-center justify-between gap-[12px] py-[18px] sm:flex-row">
            <Typography color="muted" type="body-xs">قیمت‌ها نمونه هستند و برای نمایش رابط کاربری استفاده شده‌اند.</Typography>
            <Button onPress={resetFilters} size="sm" variant="secondary">پاک کردن فیلترها ↶</Button>
          </div>
        </div>
      </div>
    </section>
  );
}
