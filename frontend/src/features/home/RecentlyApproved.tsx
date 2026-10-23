import { Avatar, Button, Typography } from "@heroui/react";
import NextLink from "next/link";

import { recentlyApproved, strings } from "@/src/lib/i18n/strings";

/** Providers recently verified or approved, with when they were added (homepage). */
export function RecentlyApproved() {
    return (
        <section className="flex flex-col">
            <div className="py-2 flex flex-row items-end justify-between gap-[16px]">
                <div className="flex flex-col gap-[8px]">
                    <Typography className="text-[28px] font-semibold" type="h2">
                        {strings.recentlyApprovedTitle}
                    </Typography>
                    <Typography className="max-w-[720px] leading-[1.8]" color="muted">
                        {strings.recentlyApprovedIntro}
                    </Typography>
                </div>

                <Button className="shrink-0 mb-[2px]" variant="ghost">
                    {strings.moreDisplay}
                </Button>
            </div>

            <hr className="mx-2" />

            {recentlyApproved.map((item) => (
                <div key={item.domain} className="flex flex-col">
                    {/* NextLink کل ردیف را می‌گیرد و hover effect دارد */}
                    <NextLink
                        className="flex flex-row items-center w-full gap-[12px] rounded-[var(--radius)] p-[12px] hover:bg-default-50 transition-colors focus-visible:outline-none"
                        href={`/companies/${encodeURIComponent(item.domain)}`}
                    >
                        <Avatar>
                            <Avatar.Fallback>{item.domain.substring(0, 2).toUpperCase()}</Avatar.Fallback>
                        </Avatar>

                        {/* flex-1 باعث می‌شود این بخش فضای خالی را پر کند و زمان به سمت راست هل داده شود */}
                        <div className="flex flex-1 flex-col gap-[2px]">
                            <Typography className="font-medium">{item.name}</Typography>
                            <Typography className="text-[12px]" color="muted" type="body">
                                {item.domain}
                            </Typography>
                        </div>

                        <Typography className="text-[12px] shrink-0" color="muted" type="body-xs">
                            {item.time}
                        </Typography>
                    </NextLink>

                    <hr className="mx-2" />
                </div>
            ))}
        </section>
    );
}