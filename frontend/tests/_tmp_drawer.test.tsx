import { render } from "@testing-library/react";
import { StrictMode } from "react";
import { Button, Drawer } from "@heroui/react";
import { vi, test, expect } from "vitest";

test("drawer full warning", () => {
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  render(
    <Drawer isOpen={true} onOpenChange={() => {}}>
      <Button>menu</Button>
      <Drawer.Backdrop>
        <Drawer.Content placement="left">
          <Drawer.Dialog aria-label="menu">
            <Drawer.CloseTrigger />
            <Drawer.Header>h</Drawer.Header>
            <Drawer.Body>b</Drawer.Body>
            <Drawer.Footer>f</Drawer.Footer>
          </Drawer.Dialog>
        </Drawer.Content>
      </Drawer.Backdrop>
    </Drawer>,
  );
  const messages = warn.mock.calls.map((c) => String(c[0]));
  warn.mockRestore();
  console.log(messages);
  expect(messages.filter((m) => m.includes("PressResponder"))).toEqual([]);
});
