"use client";

import { useTranslations } from "next-intl";
import { Modal } from "@heroui/react";
import { useRouter } from "next/navigation";
import { createContext, use, useCallback, useMemo, useState } from "react";

import { LoginForm } from "./LoginForm";
import { captureReturnUrl } from "./returnUrl";
import { useSession } from "./SessionProvider";

interface LoginDialogContextValue {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  setOpen: (isOpen: boolean) => void;
}

const LoginDialogContext = createContext<LoginDialogContextValue | null>(null);

/**
 * Owns the site-wide login modal. The login experience is a modal over the current page
 * (header, guest gates, and menu items open it) rather than a separate page, so the user
 * never leaves the surface they were on. The return URL is captured when the dialog opens,
 * so a successful login returns the user to the page they triggered it from.
 */
export function LoginDialogProvider({ children }: { children: React.ReactNode }) {
  const t = useTranslations("common");
  const router = useRouter();
  const { refresh } = useSession();
  const [isOpen, setOpen] = useState(false);
  // Bumped on every open so the form remounts fresh (phone step, cleared errors).
  const [instance, setInstance] = useState(0);

  const open = useCallback(() => {
    captureReturnUrl();
    setInstance((value) => value + 1);
    setOpen(true);
  }, []);

  const close = useCallback(() => setOpen(false), []);

  const value = useMemo<LoginDialogContextValue>(
    () => ({
      isOpen,
      setOpen,
      close,
      open,
    }),
    [isOpen, close, open],
  );

  return (
    <LoginDialogContext value={value}>
      {children}
      <Modal isOpen={isOpen} onOpenChange={setOpen}>
        <Modal.Backdrop>
          <Modal.Container>
            <Modal.Dialog
              aria-label={t("login")}
              className="w-full sm:max-w-[400px]"
            >
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Heading className="text-[28px] font-semibold">
                  {t("login")}
                </Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <LoginForm
                  key={instance}
                  onSuccess={(redirectTo) => {
                    close();
                    // Refresh the app-wide identity before navigating so the header swaps the
                    // login button for the user menu without waiting for a reload.
                    void refresh();
                    router.replace(redirectTo || "/");
                  }}
                />
              </Modal.Body>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </LoginDialogContext>
  );
}

const FALLBACK: LoginDialogContextValue = {
  isOpen: false,
  // The real app always renders the header inside ``LoginDialogProvider``; outside it (an
  // isolated render) the login action is a no-op rather than a navigation side effect.
  open: () => {},
  close: () => {},
  setOpen: () => {},
};

/** Access the login dialog from any client component inside the provider. */
export function useLoginDialog(): LoginDialogContextValue {
  return use(LoginDialogContext) ?? FALLBACK;
}
