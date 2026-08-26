import Link from 'next/link';
import { Bot, ShieldCheck, ArrowRight, Zap, Target, LineChart, Cpu, Search, CheckCircle } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 selection:bg-blue-100 selection:text-blue-900">
      {/* Navigation */}
      <nav className="fixed w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="bg-[#02042b] p-1.5 rounded-lg">
                <ShieldCheck className="h-6 w-6 text-blue-400" />
              </div>
              <span className="font-bold text-xl tracking-tight text-[#02042b]">Agentic Commerce</span>
            </div>
            <div className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-sm font-medium text-slate-600 hover:text-[#02042b] transition-colors">Platform</a>
              <a href="#architecture" className="text-sm font-medium text-slate-600 hover:text-[#02042b] transition-colors">Architecture</a>
              <a href="#security" className="text-sm font-medium text-slate-600 hover:text-[#02042b] transition-colors">Security</a>
              <div className="w-px h-4 bg-slate-300"></div>
              <Link href="/buyer" className="text-sm font-medium text-slate-600 hover:text-[#02042b] transition-colors">
                Demo Storefront
              </Link>
              <Link href="/login" className="inline-flex items-center justify-center px-5 py-2 text-sm font-medium text-white bg-[#02042b] hover:bg-[#0a0f52] rounded-full transition-all shadow-sm hover:shadow-md">
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[120%] bg-gradient-to-b from-blue-50/50 to-white -z-10 clip-path-slant"></div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-8 items-center">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100/50 border border-blue-200 text-blue-800 text-sm font-medium mb-6 animate-fade-in">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                </span>
                Introducing Next-Gen AI Commerce
              </div>
              <h1 className="text-5xl lg:text-7xl font-extrabold text-[#02042b] tracking-tight leading-[1.1] mb-6">
                Intelligent <br/>
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-500">
                  Agentic Sales.
                </span>
              </h1>
              <p className="text-lg text-slate-600 mb-8 leading-relaxed max-w-lg">
                Empower your storefront with autonomous AI agents that act as personal shoppers, negotiating in real-time, executing policy-driven decisions, and maximizing your conversion funnel natively.
              </p>
              <div className="flex flex-wrap items-center gap-4">
                <Link href="/buyer" className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-white bg-[#02042b] hover:bg-[#0a0f52] rounded-full shadow-lg hover:shadow-xl transition-all">
                  Experience Demo Store <ArrowRight className="ml-2 w-5 h-5" />
                </Link>
                <Link href="/login" className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-[#02042b] bg-white border border-slate-200 hover:border-slate-300 rounded-full shadow-sm hover:shadow transition-all">
                  Merchant Portal
                </Link>
              </div>
            </div>
            
            <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
              <div className="absolute inset-0 bg-gradient-to-tr from-blue-100 to-indigo-50 rounded-3xl transform rotate-3 scale-105 -z-10"></div>
              <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden p-6 relative">
                
                {/* Mock UI for hero */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                     <div className="flex items-center gap-3">
                       <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                         <Bot className="w-5 h-5 text-white" />
                       </div>
                       <div>
                         <h3 className="font-semibold text-sm">AI Sales Agent</h3>
                         <p className="text-xs text-emerald-600 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Online & Analyzing</p>
                       </div>
                     </div>
                  </div>
                  <div className="space-y-3">
                    <div className="bg-slate-50 p-3 rounded-xl rounded-tl-none text-sm text-slate-700 max-w-[85%] border border-slate-100">
                      I noticed you're looking at the Samsung Galaxy S24. It's a great choice, but we actually have a limited-time 10% off promotion if you bundle it with the Galaxy Buds 2 Pro today.
                    </div>
                    <div className="bg-[#02042b] text-white p-3 rounded-xl rounded-tr-none text-sm max-w-[85%] ml-auto">
                      Wow, that sounds great. What's the final price?
                    </div>
                    <div className="bg-slate-50 p-3 rounded-xl rounded-tl-none text-sm text-slate-700 max-w-[85%] border border-slate-100">
                      I've applied the discount! The bundle comes down to ₹82,999. I've updated your cart, would you like to proceed to Razorpay checkout?
                    </div>
                  </div>
                  <div className="pt-4 flex justify-end">
                    <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-sm flex items-center gap-2">
                       Pay via Razorpay <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold text-[#02042b] tracking-tight">Built for modern commerce</h2>
            <p className="mt-4 text-slate-600">The platform leverages real-time intelligence to convert window shoppers into buyers, while strictly adhering to merchant guardrails.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<Bot className="w-6 h-6 text-indigo-600" />}
              title="Autonomous Agents"
              description="LangChain-powered agents that understand user intent, search catalog databases, and construct highly relevant cart payloads."
            />
            <FeatureCard 
              icon={<ShieldCheck className="w-6 h-6 text-blue-600" />}
              title="Policy-Driven Logic"
              description="Merchants set hard guardrails. The AI cannot violate maximum discount limits, margin thresholds, or unauthorized bundles."
            />
            <FeatureCard 
              icon={<LineChart className="w-6 h-6 text-emerald-600" />}
              title="Opportunity Funnel"
              description="Visualize exactly how much revenue your AI is generating. Track intents, interventions, cross-sells, and checkout conversions."
            />
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section id="architecture" className="py-24 bg-slate-50 border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
           <div className="grid lg:grid-cols-2 gap-16 items-center">
             <div>
                <h2 className="text-3xl font-bold text-[#02042b] tracking-tight mb-6">Multi-Source Federation</h2>
                <p className="text-slate-600 mb-6">
                  Agentic Commerce isn't just a single store. It federates data across multiple merchant sources allowing the AI to search a vast inventory database instantly.
                </p>
                <ul className="space-y-4">
                  <li className="flex items-start gap-3">
                    <div className="mt-1 bg-blue-100 p-1 rounded-full"><CheckCircle className="w-4 h-4 text-blue-600" /></div>
                    <span className="text-slate-700"><strong>Data Isolation:</strong> Merchants only see their own revenue, orders, and AI metrics.</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="mt-1 bg-blue-100 p-1 rounded-full"><CheckCircle className="w-4 h-4 text-blue-600" /></div>
                    <span className="text-slate-700"><strong>RBAC Authentication:</strong> Secure JWT-based access for Owners, Admins, and Operators.</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="mt-1 bg-blue-100 p-1 rounded-full"><CheckCircle className="w-4 h-4 text-blue-600" /></div>
                    <span className="text-slate-700"><strong>Razorpay Webhooks:</strong> Idempotent background processing for payment states with signature validation.</span>
                  </li>
                </ul>
             </div>
             <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
               <div className="flex flex-col gap-4">
                 <div className="p-4 border border-slate-100 rounded-lg bg-slate-50 flex items-center gap-4">
                   <div className="bg-[#02042b] w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-xl">TN</div>
                   <div>
                     <h4 className="font-semibold text-slate-800">TechNova Gaming (Primary)</h4>
                     <p className="text-sm text-slate-500">Connected to Razorpay Gateway</p>
                   </div>
                 </div>
                 <div className="p-4 border border-slate-100 rounded-lg bg-slate-50 flex items-center gap-4 opacity-70">
                   <div className="bg-amber-500 w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-xl">AZ</div>
                   <div>
                     <h4 className="font-semibold text-slate-800">Amazon (Demo)</h4>
                     <p className="text-sm text-slate-500">Federated Catalog Source</p>
                   </div>
                 </div>
                 <div className="p-4 border border-slate-100 rounded-lg bg-slate-50 flex items-center gap-4 opacity-70">
                   <div className="bg-blue-500 w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-xl">FK</div>
                   <div>
                     <h4 className="font-semibold text-slate-800">Flipkart (Demo)</h4>
                     <p className="text-sm text-slate-500">Federated Catalog Source</p>
                   </div>
                 </div>
               </div>
             </div>
           </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#02042b] py-12 text-center text-slate-400">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-center gap-2 mb-4">
            <ShieldCheck className="w-6 h-6 text-blue-400" />
            <span className="text-white font-bold text-xl">Agentic Commerce</span>
          </div>
          <p className="text-sm">Prototype Architecture Demonstration</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="bg-slate-50 border border-slate-100 p-8 rounded-2xl transition-all hover:shadow-md hover:bg-white hover:border-slate-200">
      <div className="bg-white w-12 h-12 rounded-xl border border-slate-200 shadow-sm flex items-center justify-center mb-6">
        {icon}
      </div>
      <h3 className="text-lg font-bold text-slate-800 mb-2">{title}</h3>
      <p className="text-slate-600 text-sm leading-relaxed">{description}</p>
    </div>
  );
}
