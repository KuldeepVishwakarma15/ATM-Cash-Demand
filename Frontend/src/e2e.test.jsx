// @vitest-environment jsdom
// End-to-end checks of the real UI against a RUNNING API (default http://127.0.0.1:8000).
// Start the backend first; if it is not reachable these tests are skipped.
import { afterEach, beforeAll, describe, expect, test } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App.jsx";

const API = import.meta.env.VITE_E2E_API ?? "http://127.0.0.1:8000";
const realFetch = globalThis.fetch;
const apiUp = await realFetch(`${API}/health`).then((r) => r.ok).catch(() => false);
const wait = { timeout: 15000 };
const tokenHeader = () => ({ Authorization: `Bearer ${JSON.parse(sessionStorage.getItem("cashcast.auth")).access_token}` });

async function signIn(role = "Cash Ops Officer") {
  render(<App />);
  fireEvent.click(screen.getAllByText(/Get Started/i)[0]);
  fireEvent.change(await screen.findByRole("combobox"), { target: { value: role } });
  fireEvent.click(screen.getByText(/Fill demo login/i));
  fireEvent.click(screen.getByRole("button", { name: /^Sign in/ }));
  await screen.findByLabelText(/CashCast overview/i, {}, wait);
}

describe.skipIf(!apiUp)("CashCast UI with the live API", () => {
  beforeAll(() => { globalThis.fetch = (url, options) => realFetch(`${API}${url}`, options); });
  afterEach(() => { cleanup(); sessionStorage.clear(); });

  test("sign-in opens the dashboard with real model numbers", async () => {
    await signIn();
    await waitFor(() => expect(document.body.textContent).toMatch(/\d\d\.\d%/), wait);
    expect(document.body.textContent).toMatch(/ATM001/);
    expect(document.body.textContent).not.toMatch(/could not be loaded/i);
  });

  test("selecting an ATM updates its forecast, cash and accuracy", async () => {
    await signIn();
    const selector = await screen.findByRole("combobox", { name: "Select ATM" });
    expect(selector.querySelectorAll("option")).toHaveLength(11);
    fireEvent.change(selector, { target: { value: "ATM010" } });
    await waitFor(() => {
      expect(document.querySelector(".cc-withdrawal-chart h2")?.textContent).toContain("ATM010");
      expect(document.querySelectorAll(".cc-chart-bars > span")).toHaveLength(31);
      expect(document.querySelector(".cc-cash-on-hand h2")?.textContent).toContain("ATM010");
      expect(document.querySelector(".cc-kpi-progress[aria-label='Forecast accuracy']")?.getAttribute("aria-valuenow")).toBe("92.64842730965456");
    }, wait);
    expect(document.querySelector(".cc-tomorrow-value")).toBeNull();
  });

  test("profile button shows signed-in account details", async () => {
    await signIn();
    fireEvent.click(screen.getByRole("button", { name: "Open profile" }));
    expect(screen.getByText("ops@bankmuscat.demo")).toBeTruthy();
    expect(screen.getByText("Cash Ops Officer")).toBeTruthy();
    expect(screen.getByText("Bank Muscat")).toBeTruthy();
  });

  test("what-if adjustment updates forecast values from the API", async () => {
    await signIn();
    fireEvent.click(screen.getAllByRole("button", { name: /^What-if forecast$/ })[0]);
    const scenarioRow = await screen.findByText("Adjusted ATM demand");
    const resultRow = scenarioRow.parentElement.querySelector(".cc-table-row:not(.cc-table-head)");
    const before = resultRow.querySelectorAll("span")[2].textContent;
    fireEvent.change(screen.getByRole("slider", { name: /Demand adjustment/ }), { target: { value: "20" } });
    await waitFor(() => {
      expect(screen.getByText("+20%")).toBeTruthy();
      expect(resultRow.querySelectorAll("span")[2].textContent).not.toBe(before);
    }, wait);
  });

  test("van capacity is entered in lakh and estimates trips correctly", async () => {
    await signIn();
    fireEvent.click(screen.getAllByRole("button", { name: /^Replenishment$/ })[0]);
    fireEvent.click(await screen.findByRole("button", { name: /Select suggested/i }, wait));
    fireEvent.change(screen.getByRole("spinbutton", { name: /Cash per van/ }), { target: { value: "5" } });
    await waitFor(() => {
      const estimate = document.querySelectorAll(".cc-trip-result")[2];
      expect(estimate.textContent).toContain("28");
    }, wait);
  });

  test("ATMs without a refill recommendation cannot be selected", async () => {
    await signIn();
    fireEvent.click(screen.getAllByRole("button", { name: /^Replenishment$/ })[0]);
    const noRefill = await screen.findByRole("checkbox", { name: /ATM004.*₹0/ });
    expect(noRefill.disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Select suggested/i }));
    expect(document.querySelectorAll(".cc-replen-item input:checked")).toHaveLength(8);
  });

  test("admin threshold controls update status rules", async () => {
    await signIn("Admin");
    fireEvent.click(screen.getAllByRole("button", { name: /^Settings$/ })[0]);
    const threshold = screen.getByRole("slider", { name: /Refill soon below/ });
    expect(threshold.disabled).toBe(false);
    fireEvent.change(threshold, { target: { value: "4" } });
    expect(screen.getByText("4.0 days")).toBeTruthy();
  });

  test("a wrong password shows the real error and nothing is stored", async () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Get Started/i)[0]);
    fireEvent.change(screen.getByPlaceholderText(/you@bankmuscat/i), { target: { value: "ops@bankmuscat.demo" } });
    fireEvent.change(screen.getByPlaceholderText(/Enter your password/i), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /^Sign in/ }));
    await screen.findByText(/Incorrect email, password, or selected role/i, {}, wait);
    expect(sessionStorage.getItem("cashcast.auth")).toBeNull();
  });

  test("every dashboard page renders without errors", async () => {
    await signIn();
    const headings = { ATMs: /ATM network/, "What-if forecast": /What-if forecast/, Replenishment: /Replenishment plan/, Alerts: /^Alerts$/, Settings: /^Settings$/, Overview: /Cash Demand/ };
    for (const [name, heading] of Object.entries(headings)) {
      fireEvent.click(screen.getAllByRole("button", { name: new RegExp(`^${name}$`) })[0]);
      await screen.findByRole("heading", { level: 1, name: heading }, wait);
      expect(document.body.textContent, name).not.toMatch(/undefined|NaN|\[object Object\]/);
    }
  });

  test("a Cash Ops Officer can schedule a dispatch and MySQL stores it", async () => {
    await signIn();
    fireEvent.click(screen.getAllByRole("button", { name: /^Replenishment$/ })[0]);
    await screen.findByRole("heading", { level: 1, name: /Replenishment plan/ }, wait);
    const before = await (await fetch("/dispatches", { headers: tokenHeader() })).json();
    fireEvent.click(await screen.findByRole("button", { name: /Select suggested/i }, wait));
    fireEvent.click(screen.getByRole("button", { name: /Schedule selected/i }));
    await waitFor(async () => {
      const after = await (await fetch("/dispatches", { headers: tokenHeader() })).json();
      expect(after.count).toBeGreaterThan(before.count);
    }, wait);
  });

  test("a Viewer cannot dispatch, in the UI or in the API", async () => {
    await signIn("Viewer");
    fireEvent.click(screen.getAllByRole("button", { name: /^Replenishment$/ })[0]);
    const button = await screen.findByRole("button", { name: /Viewer cannot dispatch/i }, wait);
    expect(button.disabled).toBe(true);
    const denied = await fetch("/dispatch", { method: "POST", headers: { ...tokenHeader(), "Content-Type": "application/json" }, body: JSON.stringify({ atm_ids: ["ATM001"] }) });
    expect(denied.status).toBe(403);
  });

  test("the session survives a refresh and sign-out clears it", async () => {
    await signIn();
    cleanup();
    render(<App />);
    await screen.findByLabelText(/CashCast overview/i, {}, wait);
    fireEvent.click(screen.getAllByRole("button", { name: /^Settings$/ })[0]);
    fireEvent.click((await screen.findAllByText(/Sign out/i))[0]);
    await waitFor(() => expect(sessionStorage.getItem("cashcast.auth")).toBeNull());
  });
});
