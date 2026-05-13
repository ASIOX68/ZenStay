import React, { useState } from "react";
import { format } from "date-fns";
import { fr as frLocale, enUS } from "date-fns/locale";
import { CalendarIcon } from "lucide-react";
import { Calendar } from "./ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Button } from "./ui/button";
import { useLang } from "../contexts/LanguageContext";

export default function DateRangePicker({ range, onChange, testid = "date-range-picker" }) {
  const { lang, t } = useLang();
  const [open, setOpen] = useState(false);
  const locale = lang === "fr" ? frLocale : enUS;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const display = range?.from
    ? range.to
      ? `${format(range.from, "d MMM", { locale })} → ${format(range.to, "d MMM", { locale })}`
      : `${format(range.from, "d MMM", { locale })} → …`
    : t.booking.pick_dates;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className="w-full justify-start h-12 rounded-xl font-normal"
          data-testid={testid}
        >
          <CalendarIcon className="mr-2 h-4 w-4 text-primary" />
          <span className={range?.from ? "" : "text-muted-foreground"}>{display}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="range"
          numberOfMonths={2}
          locale={locale}
          selected={range}
          onSelect={(r) => {
            onChange(r);
            if (r?.from && r?.to) setOpen(false);
          }}
          disabled={(d) => d < today}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
}
