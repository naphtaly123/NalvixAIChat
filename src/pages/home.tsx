import { ChatWidget } from "../components/chat-widget";

export default function Home() {
  return (
    <main className="min-h-screen bg-linear-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto py-20">
        {/* Hero Section */}
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-5xl font-bold text-slate-900 dark:text-white">
              Turn Your Website Into a 24/7 Sales & Support Engine
            </h1>

            <p className="text-xl text-slate-600 dark:text-slate-300">
              Powered by <b>Nalvix AI</b> - An AI Solutions and Intelligent Automation
              company focused on solving real business problems through the
              practical application of artificial intelligence, data, and modern
              software systems.
            </p>
          </div>

          {/* Feature Cards */}
          <div className="grid md:grid-cols-3 gap-6 mt-12">
            {[
              {
                title: "Capture More Leads",
                description:
                  "Engage every visitor automatically and collect qualified leads in real-time.",
                icon: "📈",
              },
              {
                title: "Reduce Support Costs",
                description:
                  "Automate repetitive customer inquiries and free your team to focus on high-value tasks.",
                icon: "⚙️",
              },
              {
                title: "Smart AI Conversations",
                description:
                  "Nalvix AI understands context, learns from interactions, and delivers human-like responses.",
                icon: "🤖",
              },
            ].map((feature, i) => (
              <div
                key={i}
                className="bg-white dark:bg-slate-800 p-8 rounded-xl shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-slate-600 dark:text-slate-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>

          {/* Content Section */}
          <div className="mt-16 space-y-6 text-left max-w-xl mx-auto">
            <div className="bg-white dark:bg-slate-800 p-8 rounded-xl shadow-sm">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
                How Nalvix Chat Works For Your Business
              </h2>

              <ol className="space-y-3 text-slate-700 dark:text-slate-300">
                <li className="flex gap-3">
                  <span className="font-bold text-blue-600">1.</span>
                  <span>Visitors land on your website</span>
                </li>
                <li className="flex gap-3">
                  <span className="font-bold text-blue-600">2.</span>
                  <span>
                    Nalvix Chat engages them instantly through intelligent
                    conversation
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="font-bold text-blue-600">3.</span>
                  <span>
                    You capture leads, answer questions, and convert interest
                    into action
                  </span>
                </li>
              </ol>
            </div>

            <div className="bg-linear-to-r from-blue-50 to-purple-50 dark:from-slate-800 dark:to-slate-800 p-8 rounded-xl border border-blue-200 dark:border-slate-700">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                🚀 Why Businesses Choose Nalvix Chat
              </h2>
              <p className="text-slate-700 dark:text-slate-300">
                Nalvix Chat integrates seamlessly into your website or mobile application with minimal
                setup. No complex systems. No heavy infrastructure. Just
                intelligent automation that works from day one.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Widget */}
      <ChatWidget />
    </main>
  );
}
