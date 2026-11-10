"use client";

import { Chip, Modal, Typography } from "@heroui/react";
import { HelpCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type { Reason } from "@/src/lib/api/explanations";

import { reasonSentences } from "../explanationText";

/** A small "why this plan?" badge that opens a modal with the explanation. */
export function WhyRecommended({ reasons }: { reasons: Reason[] }) {
  const ot = useTranslations();
  const [open, setOpen] = useState(false);
  const sentences = reasonSentences(reasons, ot);

  if (!sentences.length) return null;

  return (
    <>
      <button
        aria-label={ot("explainReasonLabel")}
        className="absolute left-3 top-3 z-10"
        type="button"
        onClick={() => setOpen(true)}
      >
        <Chip
          color="accent"
          size="sm"
          variant="soft"
          className="size-7 justify-center rounded-full p-0"
        >
          <HelpCircle aria-hidden className="size-4" />
        </Chip>
      </button>
      <Modal isOpen={open} onOpenChange={setOpen}>
        <Modal.Backdrop>
          <Modal.Container size="sm">
            <Modal.Dialog aria-label={ot("explainReasonLabel")}>
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Heading className="text-[18px] font-semibold">
                  {ot("explainReasonLabel")}
                </Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <ul className="flex flex-col gap-[8px]">
                  {sentences.map((sentence, index) => (
                    <li key={index} className="list-none">
                      <Typography
                        className="text-[14px] leading-[1.9]"
                        type="body"
                      >
                        {sentence}
                      </Typography>
                    </li>
                  ))}
                </ul>
              </Modal.Body>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </>
  );
}
