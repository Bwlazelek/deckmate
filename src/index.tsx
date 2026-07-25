import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  TextField,
  staticClasses,
} from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useEffect, useState } from "react";
import { FaRobot } from "react-icons/fa";

interface DeckStatus {
  ready: boolean;
  mode: string;
  root_enabled: boolean;
  arbitrary_shell_enabled: boolean;
  game_count: number;
  message: string;
}

interface PlanAction {
  type: string;
  label: string;
  risk: string;
  description: string;
}

interface Plan {
  id: string;
  status: string;
  title: string;
  summary: string;
  topic: string;
  risk: string;
  actions: PlanAction[];
  limitations: string[];
}

interface PlanResponse {
  ok: boolean;
  plan?: Plan;
  error?: string;
}

interface Operation {
  id: string;
  plan_id: string;
  status: string;
  summary: string;
  rollback_available: boolean;
  results: Array<Record<string, unknown>>;
}

interface OperationResponse {
  ok: boolean;
  operation?: Operation;
  error?: string;
}

const getStatus = callable<[], DeckStatus>("get_status");
const submitPrompt = callable<[prompt: string], PlanResponse>("submit_prompt");
const executePlan = callable<[planId: string], OperationResponse>("execute_plan");
const cancelPlan = callable<[planId: string], PlanResponse>("cancel_plan");
const rollbackLast = callable<[], OperationResponse>("rollback_last");

const palette = {
  panel: "rgba(13, 20, 31, 0.92)",
  card: "rgba(31, 45, 61, 0.82)",
  border: "rgba(102, 199, 255, 0.35)",
  blue: "#66c7ff",
  green: "#64d98b",
  amber: "#f6c85f",
  muted: "#a9b7c6",
};

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: palette.card,
        border: `1px solid ${palette.border}`,
        borderRadius: 10,
        padding: 12,
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      {children}
    </div>
  );
}

function Content() {
  const [status, setStatus] = useState<DeckStatus | null>(null);
  const [prompt, setPrompt] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastMessage, setLastMessage] = useState("Ask DeckMate to inspect or prepare a setup task.");

  useEffect(() => {
    getStatus()
      .then(setStatus)
      .catch((error) => setLastMessage(`Backend unavailable: ${String(error)}`));
  }, []);

  const requestPlan = async (request: string) => {
    const trimmed = request.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setLastMessage("Inspecting your request and building a safe plan…");
    try {
      const response = await submitPrompt(trimmed);
      if (!response.ok || !response.plan) throw new Error(response.error ?? "No plan returned");
      setPlan(response.plan);
      setPrompt("");
      setLastMessage("Plan ready. Review every action before approving it.");
    } catch (error) {
      setLastMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!plan || busy) return;
    setBusy(true);
    setLastMessage("Running approved typed actions…");
    try {
      const response = await executePlan(plan.id);
      if (!response.ok || !response.operation) throw new Error(response.error ?? "Execution failed");
      setPlan(null);
      setLastMessage(`${response.operation.summary} completed. No Steam or game files were changed in v0.1.`);
      toaster.toast({ title: "DeckMate completed the plan", body: "A reversible operation receipt was created." });
      const nextStatus = await getStatus();
      setStatus(nextStatus);
    } catch (error) {
      setLastMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!plan || busy) return;
    await cancelPlan(plan.id);
    setPlan(null);
    setLastMessage("Plan cancelled. Nothing was changed.");
  };

  const undo = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await rollbackLast();
      if (!response.ok || !response.operation) throw new Error(response.error ?? "Nothing to undo");
      setLastMessage(`Rolled back: ${response.operation.summary}`);
      toaster.toast({ title: "DeckMate rollback complete", body: response.operation.summary });
    } catch (error) {
      setLastMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ background: palette.panel, minHeight: "100%", paddingBottom: 12 }}>
      <PanelSection title="System">
        <PanelSectionRow>
          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <strong style={{ color: status?.ready ? palette.green : palette.amber }}>
                {status?.ready ? "● Ready" : "● Connecting"}
              </strong>
              <span style={{ color: palette.muted }}>{status?.game_count ?? 0} games found</span>
            </div>
            <div style={{ color: palette.muted, fontSize: 12, marginTop: 7 }}>
              Non-root · no arbitrary shell · approval required
            </div>
          </Card>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Ask DeckMate">
        <PanelSectionRow>
          <TextField
            label="What should I set up?"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={busy || !prompt.trim()} onClick={() => requestPlan(prompt)}>
            {busy ? "Working…" : "Build a safe plan"}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <Card>
            <div style={{ color: palette.blue, fontWeight: 600, marginBottom: 5 }}>DeckMate</div>
            <div style={{ lineHeight: 1.35 }}>{lastMessage}</div>
          </Card>
        </PanelSectionRow>
      </PanelSection>

      {!plan && (
        <PanelSection title="Quick requests">
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => requestPlan("Show my installed Steam games")}>Inspect my game library</ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => requestPlan("Install GE-Proton for my selected game")}>Prepare a GE-Proton setup</ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => requestPlan("Set up FSR for my selected game")}>Prepare an FSR setup</ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => requestPlan("Set up EmuDeck and emulation")}>Prepare an EmuDeck setup</ButtonItem>
          </PanelSectionRow>
        </PanelSection>
      )}

      {plan && (
        <PanelSection title="Approval required">
          <PanelSectionRow>
            <Card>
              <div style={{ color: palette.blue, fontSize: 18, fontWeight: 700 }}>{plan.title}</div>
              <div style={{ color: palette.muted, marginTop: 7, lineHeight: 1.35 }}>{plan.summary}</div>
              <div style={{ color: palette.amber, marginTop: 9, fontSize: 12 }}>Risk: {plan.risk}</div>
            </Card>
          </PanelSectionRow>
          {plan.actions.map((action, index) => (
            <PanelSectionRow key={`${action.type}-${index}`}>
              <Card>
                <div style={{ fontWeight: 650 }}>{index + 1}. {action.label}</div>
                <div style={{ color: palette.muted, fontSize: 12, marginTop: 5 }}>{action.description}</div>
                <div style={{ color: action.risk === "read-only" ? palette.green : palette.amber, fontSize: 11, marginTop: 5 }}>
                  {action.risk}
                </div>
              </Card>
            </PanelSectionRow>
          ))}
          <PanelSectionRow>
            <ButtonItem layout="below" disabled={busy} onClick={approve}>Approve and run</ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" disabled={busy} onClick={cancel}>Cancel—change nothing</ButtonItem>
          </PanelSectionRow>
        </PanelSection>
      )}

      <PanelSection title="Recovery">
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={busy} onClick={undo}>Undo last DeckMate operation</ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </div>
  );
}

export default definePlugin(() => ({
  name: "DeckMate",
  titleView: <div className={staticClasses.Title}>DeckMate</div>,
  content: <Content />,
  icon: <FaRobot />,
  onDismount() {
    console.log("DeckMate frontend unloaded");
  },
}));
