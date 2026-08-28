import React from "react";
import { Activity, CheckCircle2, ChevronRight, CircleDashed, ServerCrash, Bot, Wrench, AlertCircle, Loader2 } from "lucide-react";

export interface OrchestrationEvent {
  type: string;
  node?: string;
  status?: string;
  tool_calls?: any[];
  tool_results?: any[];
  message?: string;
  timestamp: number;
  intent?: any;
  merchants?: string[];
  products_found?: number;
  ranked_count?: number;
}

interface AgentOrchestrationProps {
  events: OrchestrationEvent[];
  isExecuting: boolean;
  error?: string | null;
}

export function AgentOrchestration({ events, isExecuting, error }: AgentOrchestrationProps) {
  // Derive visual steps from the raw events
  const steps: { label: string; status: 'pending' | 'running' | 'completed' | 'error'; details?: string[] }[] = [
    { label: "Request Received", status: isExecuting || events.length > 0 ? "completed" : "pending" }
  ];

  let hasFinalAgentPass = false;

  events.forEach((ev) => {
    if (ev.type === "orchestration") {
      if (ev.node === "plan") {
        const intent = ev.intent || {};
        steps.push({
          label: "Intent & Planning",
          status: "completed",
          details: [
            `Search product: ${intent.query || 'N/A'}`,
            `Maximum price: ${intent.max_price ? '₹' + intent.max_price : 'N/A'}`,
            `Merchant scope: all available`
          ]
        });
      } else if (ev.node === "discover") {
        // Handled as part of search/commerce agent
      } else if (ev.node === "search") {
        steps.push({
          label: "Search/Commerce Agent",
          status: "completed",
          details: [
            "Searching application catalog",
            "Amazon",
            "Flipkart",
            "Razorpay-connected merchants"
          ]
        });
        steps.push({
          label: "Products Found",
          status: "completed",
          details: [`Found ${ev.products_found || 0} products`]
        });
      } else if (ev.node === "rank") {
        steps.push({
          label: "Ranking",
          status: "completed"
        });
      } else if (ev.node === "agent") {
        if (ev.tool_calls && ev.tool_calls.length > 0) {
          steps.push({
            label: "Agent Actions",
            status: "completed",
            details: ev.tool_calls.map(tc => `Planning to use: ${tc.name.replace(/_/g, ' ')}`)
          });
        } else {
          hasFinalAgentPass = true;
          steps.push({
            label: "Response Generation",
            status: "completed"
          });
        }
      } else if (ev.node === "tools") {
        const toolsUsed = ev.tool_results?.map(tr => tr.tool.replace(/_/g, ' ')) || [];
        steps.push({
          label: "Agent Actions",
          status: "completed",
          details: toolsUsed.length > 0 ? toolsUsed : ["Executed backend tools"]
        });
      }
    }
  });

  if (error) {
    steps.push({
      label: "Execution Failed",
      status: "error",
      details: [error]
    });
  } else if (isExecuting) {
    if (!hasFinalAgentPass) {
      steps.push({
        label: "Processing",
        status: "running"
      });
    } else {
      steps.push({
        label: "Finalizing",
        status: "running"
      });
    }
  } else if (events.length > 0) {
    steps.push({
      label: "Execution Completed",
      status: "completed"
    });
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-200 font-mono text-sm border-l border-slate-800">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h2 className="font-semibold text-slate-100 uppercase tracking-wider text-xs">LangGraph Execution</h2>
        </div>
        {isExecuting && (
          <div className="flex items-center gap-2 text-xs text-indigo-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Running</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {events.length === 0 && !isExecuting && !error ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3 opacity-50">
            <Bot className="w-8 h-8" />
            <p>Waiting for agent requests...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {steps.map((step, idx) => (
              <div key={idx} className="relative flex items-start gap-3">
                {/* Connecting line */}
                {idx !== steps.length - 1 && (
                  <div className="absolute top-6 left-2.5 w-px h-[calc(100%+8px)] bg-slate-700 -z-10" />
                )}

                {/* Icon */}
                <div className="bg-slate-900 z-10 pt-0.5">
                  {step.status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : step.status === 'running' ? (
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                  ) : step.status === 'error' ? (
                    <ServerCrash className="w-5 h-5 text-red-500" />
                  ) : (
                    <CircleDashed className="w-5 h-5 text-slate-600" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 pb-1">
                  <div className={`font-medium ${step.status === 'completed' ? 'text-slate-200' :
                      step.status === 'running' ? 'text-indigo-300' :
                        step.status === 'error' ? 'text-red-400' : 'text-slate-500'
                    }`}>
                    {step.label}
                  </div>

                  {step.details && step.details.length > 0 && (
                    <div className="mt-2 space-y-1.5">
                      {step.details.map((detail, dIdx) => (
                        <div key={dIdx} className="flex items-start gap-2 text-xs text-slate-400 bg-slate-800/50 p-2 rounded-md border border-slate-700/50">
                          {step.status === 'error' ? (
                            <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                          ) : step.label === 'Agent Actions' ? (
                            <Wrench className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                          )}
                          <span className="leading-relaxed">{detail}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
