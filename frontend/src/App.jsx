import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Video, Film, Wand2, Play, Pause, RefreshCw, CheckCircle2, 
  AlertCircle, ChevronRight, Sliders, Volume2, Type, Smartphone, 
  Monitor, ArrowRight, Eye, ShieldCheck, Zap, Download, Layers, Flame
} from 'lucide-react';

const GENRES = [
  {
    id: "mythology",
    label: "Mythology & Legends",
    description: "Epic volumetric lighting, ancient secrets, dramatic divine reveals",
    icon: "🏛️",
    accent: "from-amber-500/20 to-orange-500/20 border-amber-500/40 text-amber-300"
  },
  {
    id: "informative",
    label: "Informative & Science",
    description: "Macro details, futuristic laboratory aesthetics, high-curiosity breakthroughs",
    icon: "🔬",
    accent: "from-blue-500/20 to-cyan-500/20 border-blue-500/40 text-blue-300"
  },
  {
    id: "funny",
    label: "Comedy & Satire",
    description: "Punchy pop pacing, exaggerated expressions, vibrant colorful chaos",
    icon: "😂",
    accent: "from-pink-500/20 to-rose-500/20 border-pink-500/40 text-pink-300"
  },
  {
    id: "dark_mystery",
    label: "Dark Mystery & Noir",
    description: "Chiaroscuro shadows, classified files, eerie psychological hooks",
    icon: "🕵️",
    accent: "from-purple-500/20 to-indigo-500/20 border-purple-500/40 text-purple-300"
  },
  {
    id: "sci_fi",
    label: "Sci-Fi & Cyberpunk",
    description: "Anamorphic neon flares, holographic tech, cosmic stakes",
    icon: "🚀",
    accent: "from-emerald-500/20 to-teal-500/20 border-emerald-500/40 text-emerald-300"
  }
];

const VOICES = [
  { id: "en-US-ChristopherNeural", name: "Christopher (Documentary & Deep)", desc: "Authoritative, cinematic narration" },
  { id: "en-US-GuyNeural", name: "Guy (Energetic & Fast)", desc: "Punchy, casual social media cadence" },
  { id: "en-US-JennyNeural", name: "Jenny (Clear & Articulate)", desc: "Engaging, natural storytelling" },
  { id: "en-US-EricNeural", name: "Eric (Dramatic & Bass)", desc: "Low resonant cinematic tone" },
  { id: "en-GB-RyanNeural", name: "Ryan (British Classic)", desc: "Sophisticated lore and history" }
];

export default function App() {
  // Step navigation: 1: Hooks & Ideation, 2: Storyboard, 3: Studio & Render
  const [activeStep, setActiveStep] = useState(1);
  
  // Generation inputs
  const [topic, setTopic] = useState("Roman Self-Healing Concrete");
  const [genre, setGenre] = useState("informative");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [selectedVoice, setSelectedVoice] = useState("en-US-ChristopherNeural");
  const [subtitleStyle, setSubtitleStyle] = useState("hormozi_bold");
  
  // LangGraph Hook State
  const [isGeneratingHooks, setIsGeneratingHooks] = useState(false);
  const [hookData, setHookData] = useState(null);
  const [selectedHook, setSelectedHook] = useState(null);
  
  // Storyboard State
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [scriptData, setScriptData] = useState(null);
  
  // Video Rendering State
  const [isRendering, setIsRendering] = useState(false);
  const [renderJob, setRenderJob] = useState(null);
  const [renderProgress, setRenderProgress] = useState(0);
  const [renderStatusText, setRenderStatusText] = useState("");
  const [videoResultUrl, setVideoResultUrl] = useState(null);

  // Quick suggestions
  const topicSuggestions = [
    "Roman Self-Healing Concrete",
    "The Voynich Manuscript",
    "Why Samurai Used Incense Clocks",
    "What If Earth Stopped Spinning for 1 Second?",
    "The Secret Psychology of Casinos"
  ];

  // Run LangGraph Hook Engine
  const handleGenerateHooks = async () => {
    setIsGeneratingHooks(true);
    setHookData(null);
    setSelectedHook(null);
    try {
      const res = await fetch('/api/hooks/generate-and-verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          genre,
          aspect_ratio: aspectRatio,
          min_pass_score: 80,
          max_iterations: 3
        })
      });
      const data = await res.json();
      setHookData(data);
      if (data.winning_hook) {
        setSelectedHook(data.winning_hook);
      }
    } catch (err) {
      console.error("Hook generation failed:", err);
    } finally {
      setIsGeneratingHooks(false);
    }
  };

  // Generate Script & Move to Step 2
  const handleGenerateScript = async () => {
    setIsGeneratingScript(true);
    try {
      const res = await fetch('/api/scripts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          genre,
          aspect_ratio: aspectRatio,
          target_duration_sec: 30,
          selected_hook: selectedHook
        })
      });
      const data = await res.json();
      setScriptData(data);
      setActiveStep(2);
    } catch (err) {
      console.error("Script generation failed:", err);
    } finally {
      setIsGeneratingScript(false);
    }
  };

  // Trigger Video Render
  const handleStartRender = async () => {
    if (!scriptData) return;
    setIsRendering(true);
    setRenderProgress(10);
    setRenderStatusText("Initializing Production Pipeline...");
    
    try {
      const res = await fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script: scriptData,
          voice_name: selectedVoice,
          subtitle_style: subtitleStyle,
          aspect_ratio: aspectRatio,
          include_bg_music: true
        })
      });
      const data = await res.json();
      setRenderJob(data);

      // Poll status
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/video/status/${data.job_id}`);
          const statusData = await statusRes.json();
          
          setRenderProgress(statusData.progress_percent || 30);
          if (statusData.status === "generating_voicoever") setRenderStatusText("Synthesizing Neural Audio...");
          else if (statusData.status === "generating_visuals") setRenderStatusText("Rendering Visual Scenes & Camera Motion...");
          else if (statusData.status === "compositing_video") setRenderStatusText("Assembling Timeline in FFmpeg...");
          else if (statusData.status === "burning_subtitles") setRenderStatusText("Burning Hormozi-Style Subtitles...");

          if (statusData.status === "completed") {
            clearInterval(pollInterval);
            setIsRendering(false);
            setRenderProgress(100);
            setRenderStatusText("Video Generated Successfully!");
            setVideoResultUrl(statusData.video_url);
          } else if (statusData.status === "failed") {
            clearInterval(pollInterval);
            setIsRendering(false);
            setRenderStatusText(`Render Failed: ${statusData.error_message}`);
          }
        } catch (e) {
          console.error("Poll error:", e);
        }
      }, 2000);
    } catch (err) {
      console.error("Render request failed:", err);
      setIsRendering(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Film className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">CineShorts AI</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-medium">
                  LangGraph Engine
                </span>
              </div>
              <p className="text-xs text-slate-400">Viral Hook Architecture to Generative Cinema</p>
            </div>
          </div>

          {/* Format Selector in Header */}
          <div className="flex items-center space-x-4">
            <div className="bg-slate-800/80 p-1 rounded-xl border border-slate-700/60 flex items-center space-x-1">
              <button
                onClick={() => setAspectRatio("9:16")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  aspectRatio === "9:16" 
                    ? "bg-indigo-600 text-white shadow" 
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Smartphone className="w-3.5 h-3.5" />
                <span>9:16 Shorts/Reels</span>
              </button>
              <button
                onClick={() => setAspectRatio("16:9")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  aspectRatio === "16:9" 
                    ? "bg-indigo-600 text-white shadow" 
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Monitor className="w-3.5 h-3.5" />
                <span>16:9 Cinematic</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stepper Navigation */}
      <div className="border-b border-slate-800 bg-slate-900/30 py-3">
        <div className="max-w-4xl mx-auto px-4 flex items-center justify-between">
          <button 
            onClick={() => setActiveStep(1)}
            className={`flex items-center space-x-2 text-sm font-medium transition-colors ${
              activeStep === 1 ? "text-indigo-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              activeStep === 1 ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"
            }`}>1</span>
            <span>Hook Lab & Critic</span>
          </button>
          
          <ChevronRight className="w-4 h-4 text-slate-600" />

          <button 
            onClick={() => scriptData && setActiveStep(2)}
            disabled={!scriptData}
            className={`flex items-center space-x-2 text-sm font-medium transition-colors ${
              !scriptData ? "opacity-50 cursor-not-allowed text-slate-500" :
              activeStep === 2 ? "text-indigo-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              activeStep === 2 ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"
            }`}>2</span>
            <span>Scene Storyboard</span>
          </button>

          <ChevronRight className="w-4 h-4 text-slate-600" />

          <button 
            onClick={() => scriptData && setActiveStep(3)}
            disabled={!scriptData}
            className={`flex items-center space-x-2 text-sm font-medium transition-colors ${
              !scriptData ? "opacity-50 cursor-not-allowed text-slate-500" :
              activeStep === 3 ? "text-indigo-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              activeStep === 3 ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"
            }`}>3</span>
            <span>Studio Production</span>
          </button>
        </div>
      </div>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        
        {/* STEP 1: HOOK LABORATORY & CRITIC */}
        {activeStep === 1 && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Topic & Genre Card */}
            <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                  <Flame className="w-5 h-5 text-amber-400" />
                  <span>Topic & Viral Angle</span>
                </h2>
                <span className="text-xs text-slate-400">Step 1: Psychological Hook Formulation</span>
              </div>

              {/* Topic Input */}
              <div className="space-y-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Video Concept / Core Story Idea
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Ancient Roman Self-Healing Concrete or The Voynich Manuscript"
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-3.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm shadow-inner"
                  />
                </div>

                {/* Suggestions */}
                <div className="flex flex-wrap gap-2 pt-1">
                  <span className="text-xs text-slate-500 self-center">Trending ideas:</span>
                  {topicSuggestions.map((sug, i) => (
                    <button
                      key={i}
                      onClick={() => setTopic(sug)}
                      className="text-xs px-2.5 py-1 rounded-full bg-slate-800/60 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition-colors"
                    >
                      {sug}
                    </button>
                  ))}
                </div>
              </div>

              {/* Genre Selector */}
              <div className="mt-6 space-y-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Select Visual & Narrative Genre
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                  {GENRES.map((g) => {
                    const isSelected = genre === g.id;
                    return (
                      <button
                        key={g.id}
                        onClick={() => setGenre(g.id)}
                        className={`text-left p-4 rounded-xl border transition-all relative overflow-hidden flex flex-col justify-between ${
                          isSelected
                            ? `bg-gradient-to-b ${g.accent} shadow-lg ring-1 ring-white/20`
                            : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/50"
                        }`}
                      >
                        <div>
                          <div className="text-2xl mb-2">{g.icon}</div>
                          <h3 className="font-semibold text-sm text-white">{g.label}</h3>
                          <p className="text-xs text-slate-400 mt-1 line-clamp-2">{g.description}</p>
                        </div>
                        {isSelected && (
                          <div className="mt-3 flex items-center space-x-1 text-[11px] font-medium text-white/90">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Selected</span>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Generate Hook Button */}
              <div className="mt-6 flex justify-end">
                <button
                  onClick={handleGenerateHooks}
                  disabled={isGeneratingHooks || !topic.trim()}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-medium text-sm flex items-center space-x-2 shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
                >
                  {isGeneratingHooks ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Running LangGraph Verifier...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 text-amber-300" />
                      <span>Synthesize & Verify Viral Hooks</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* HOOK RESULTS & CRITIC EVALUATION */}
            {hookData && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <span>LangGraph Adversarial Critic Analysis</span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Iterations Run: {hookData.total_iterations} | Approved Threshold: 80/100
                    </p>
                  </div>
                </div>

                {/* Candidate Hook Cards */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {hookData.all_iterations?.[hookData.all_iterations.length - 1]?.candidates?.map((cand, idx) => {
                    const isSelected = selectedHook?.id === cand.id;
                    const evalObj = hookData.all_iterations?.[hookData.all_iterations.length - 1]?.evaluations?.find(
                      e => e.hook_id === cand.id
                    );
                    const score = evalObj?.total_score || 85;
                    const passed = score >= 80;

                    return (
                      <div
                        key={cand.id}
                        onClick={() => setSelectedHook(cand)}
                        className={`cursor-pointer rounded-2xl border p-5 flex flex-col justify-between transition-all relative ${
                          isSelected
                            ? "bg-slate-900 border-indigo-500 shadow-xl shadow-indigo-500/10 ring-1 ring-indigo-500"
                            : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <div>
                          {/* Header badges */}
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                              {cand.archetype.replace('_', ' ')}
                            </span>
                            <div className={`flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                              passed ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            }`}>
                              <span>{score}/100</span>
                            </div>
                          </div>

                          {/* Hook Text */}
                          <p className="font-semibold text-white text-base leading-snug mb-3">
                            "{cand.text}"
                          </p>

                          {/* Visual Concept */}
                          <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800/80 mb-3 text-xs space-y-1">
                            <div className="text-slate-400 font-medium flex items-center space-x-1">
                              <Eye className="w-3.5 h-3.5 text-indigo-400" />
                              <span>0-2s Visual Hook Concept:</span>
                            </div>
                            <p className="text-slate-300 italic">{cand.visual_concept}</p>
                          </div>

                          {/* Audio SFX */}
                          <div className="flex items-center space-x-2 text-xs text-slate-400">
                            <Volume2 className="w-3.5 h-3.5 text-pink-400" />
                            <span>Audio Trigger: <code className="text-pink-300 font-mono">{cand.audio_sfx_cue}</code></span>
                          </div>
                        </div>

                        {/* Breakdown Radar Pill */}
                        <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-1.5">
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Retention Pull:</span>
                            <span className="font-medium text-slate-200">{evalObj?.retention_pull_score || 25}/30</span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Curiosity Index:</span>
                            <span className="font-medium text-slate-200">{evalObj?.curiosity_index_score || 22}/25</span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Visual Execution:</span>
                            <span className="font-medium text-slate-200">{evalObj?.visual_potential_score || 21}/25</span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Clarity & Cadence:</span>
                            <span className="font-medium text-slate-200">{evalObj?.clarity_pacing_score || 17}/20</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Critic Feedback Banner */}
                {hookData.winning_evaluation && (
                  <div className="bg-gradient-to-r from-slate-900 to-indigo-950/40 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        <span className="font-semibold text-white">Verifier Consensus: Hook Ready for Production</span>
                      </div>
                      <p className="text-xs text-slate-300 max-w-2xl">
                        {hookData.winning_evaluation.strengths?.[0] || "Hook achieves strong immediate curiosity without opening fluff."}
                      </p>
                    </div>

                    <button
                      onClick={handleGenerateScript}
                      disabled={isGeneratingScript || !selectedHook}
                      className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm flex items-center space-x-2 shadow-lg shadow-indigo-600/30 whitespace-nowrap"
                    >
                      {isGeneratingScript ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Generating Micro-Scenes...</span>
                        </>
                      ) : (
                        <>
                          <span>Build Scene Storyboard</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* STEP 2: SCENE-BY-SCENE STORYBOARD */}
        {activeStep === 2 && scriptData && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Storyboard Header */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-indigo-400">Step 2: Micro-Scene Director Timeline</span>
                <h2 className="text-xl font-bold text-white mt-1">{scriptData.title}</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Total Duration: ~{scriptData.estimated_total_duration}s | Format: {scriptData.aspect_ratio} | Genre: {scriptData.genre}
                </p>
              </div>

              <button
                onClick={() => setActiveStep(3)}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-medium text-sm flex items-center space-x-2 shadow-lg shadow-indigo-500/25"
              >
                <span>Proceed to Studio Production</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Scenes Grid / Timeline */}
            <div className="space-y-4">
              {scriptData.scenes?.map((sc, idx) => (
                <div
                  key={sc.scene_id}
                  className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-all flex flex-col lg:flex-row gap-6"
                >
                  {/* Scene Badge & Timing */}
                  <div className="w-full lg:w-48 flex-shrink-0 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-slate-800 pb-4 lg:pb-0 lg:pr-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded-lg bg-indigo-500/20 text-indigo-300 font-bold text-xs border border-indigo-500/30">
                          SCENE {sc.scene_id}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">
                          {sc.duration_sec}s
                        </span>
                      </div>
                      <div className="mt-3">
                        <span className="text-[11px] text-slate-500 uppercase font-medium">Camera Motion</span>
                        <div className="text-xs text-slate-200 font-semibold flex items-center space-x-1 mt-0.5">
                          <Layers className="w-3.5 h-3.5 text-indigo-400" />
                          <span className="capitalize">{sc.camera_motion.replace('_', ' ')}</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3">
                      <span className="text-[11px] text-slate-500 uppercase font-medium">Audio SFX Cue</span>
                      <div className="text-xs text-pink-300 font-mono mt-0.5">
                        {sc.audio_sfx_cue}
                      </div>
                    </div>
                  </div>

                  {/* Scene Details */}
                  <div className="flex-1 space-y-3">
                    {/* Voiceover */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                          <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Voiceover Narration</span>
                        </label>
                      </div>
                      <textarea
                        value={sc.voiceover_text}
                        onChange={(e) => {
                          const updated = [...scriptData.scenes];
                          updated[idx].voiceover_text = e.target.value;
                          setScriptData({ ...scriptData, scenes: updated });
                        }}
                        rows={2}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>

                    {/* Visual Prompt */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                          <Wand2 className="w-3.5 h-3.5 text-purple-400" />
                          <span>AI Visual Generation Prompt</span>
                        </label>
                        <span className="text-[11px] text-indigo-400">{sc.visual_hook_type}</span>
                      </div>
                      <textarea
                        value={sc.visual_prompt}
                        onChange={(e) => {
                          const updated = [...scriptData.scenes];
                          updated[idx].visual_prompt = e.target.value;
                          setScriptData({ ...scriptData, scenes: updated });
                        }}
                        rows={2}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-mono text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      />
                    </div>
                  </div>

                  {/* On-screen Text Overlay */}
                  <div className="w-full lg:w-56 flex-shrink-0 flex flex-col justify-center bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 text-center">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-2">
                      Subtitle Callout Overlay
                    </span>
                    <div className="bg-black/90 border border-amber-400/40 rounded-lg p-2.5 shadow">
                      <span className="font-extrabold text-xs text-amber-300 tracking-wider">
                        {sc.on_screen_text}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Retention Call to Action */}
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-xl p-4 flex items-center justify-between">
              <span className="text-xs text-slate-400">Closing Retention Loop / CTA:</span>
              <span className="text-xs font-semibold text-indigo-300">"{scriptData.call_to_action}"</span>
            </div>
          </div>
        )}

        {/* STEP 3: STUDIO PRODUCTION & VIDEO PLAYER */}
        {activeStep === 3 && scriptData && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Left Column: Production Settings */}
              <div className="lg:col-span-6 space-y-6">
                <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
                  <div>
                    <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                      <Video className="w-5 h-5 text-indigo-400" />
                      <span>Studio Compositor Engine</span>
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">Configure neural voices, subtitle typography, and audio mixing</p>
                  </div>

                  {/* Voice Selector */}
                  <div className="space-y-3">
                    <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Narrator Neural Voice (Edge-TTS / Neural)
                    </label>
                    <div className="space-y-2">
                      {VOICES.map((v) => (
                        <div
                          key={v.id}
                          onClick={() => setSelectedVoice(v.id)}
                          className={`cursor-pointer p-3.5 rounded-xl border transition-all flex items-center justify-between ${
                            selectedVoice === v.id
                              ? "bg-indigo-600/20 border-indigo-500 shadow"
                              : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                          }`}
                        >
                          <div>
                            <div className="text-sm font-medium text-white">{v.name}</div>
                            <div className="text-xs text-slate-400">{v.desc}</div>
                          </div>
                          {selectedVoice === v.id && <CheckCircle2 className="w-4 h-4 text-indigo-400" />}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Subtitle Style */}
                  <div className="space-y-3">
                    <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Dynamic Subtitle Styling
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={() => setSubtitleStyle("hormozi_bold")}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          subtitleStyle === "hormozi_bold"
                            ? "bg-amber-500/15 border-amber-400 text-amber-300"
                            : "bg-slate-950/60 border-slate-800 text-slate-300"
                        }`}
                      >
                        <div className="font-extrabold text-xs uppercase tracking-wider">HORMOZI VIRAL</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">Bold yellow & white with stroke</div>
                      </button>

                      <button
                        onClick={() => setSubtitleStyle("beast_color")}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          subtitleStyle === "beast_color"
                            ? "bg-emerald-500/15 border-emerald-400 text-emerald-300"
                            : "bg-slate-950/60 border-slate-800 text-slate-300"
                        }`}
                      >
                        <div className="font-extrabold text-xs uppercase tracking-wider">MRBEAST POP</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">High contrast green & yellow punch</div>
                      </button>
                    </div>
                  </div>

                  {/* Render Trigger */}
                  <div className="pt-2">
                    <button
                      onClick={handleStartRender}
                      disabled={isRendering}
                      className="w-full py-4 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 hover:from-indigo-400 hover:to-pink-400 text-white font-bold text-sm flex items-center justify-center space-x-2 shadow-xl shadow-purple-500/20 transition-all disabled:opacity-50"
                    >
                      {isRendering ? (
                        <>
                          <RefreshCw className="w-5 h-5 animate-spin" />
                          <span>Synthesizing Video...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5 text-amber-300" />
                          <span>Render Final MP4 Video</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Progress Status Bar */}
                  {isRendering && (
                    <div className="space-y-2 bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="text-slate-300">{renderStatusText}</span>
                        <span className="text-indigo-400">{renderProgress}%</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full transition-all duration-500 rounded-full"
                          style={{ width: `${renderProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Interactive Video Player Mockup */}
              <div className="lg:col-span-6 flex flex-col items-center justify-center">
                {aspectRatio === "9:16" ? (
                  /* Vertical Phone Frame Simulation */
                  <div className="relative w-full max-w-[340px] aspect-[9/16] bg-black rounded-[40px] border-4 border-slate-700/80 shadow-2xl overflow-hidden flex flex-col items-center justify-center ring-1 ring-white/10">
                    {/* Top Phone Notch */}
                    <div className="absolute top-3 w-28 h-5 bg-slate-900 rounded-full z-20 flex items-center justify-center">
                      <div className="w-2.5 h-2.5 rounded-full bg-slate-800 mr-2" />
                      <div className="w-3 h-3 rounded-full bg-slate-800" />
                    </div>

                    {videoResultUrl ? (
                      <video
                        src={videoResultUrl}
                        controls
                        autoPlay
                        loop
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="p-6 text-center space-y-3">
                        <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center mx-auto border border-slate-800">
                          <Play className="w-8 h-8 text-indigo-400 ml-1" />
                        </div>
                        <h4 className="text-sm font-semibold text-white">Live Video Preview</h4>
                        <p className="text-xs text-slate-400 leading-relaxed">
                          Click "Render Final MP4 Video" to synthesize TTS narration, Ken Burns dynamic visuals, and burned subtitles.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Widescreen 16:9 Cinema Monitor */
                  <div className="relative w-full aspect-video bg-black rounded-2xl border-2 border-slate-800 shadow-2xl overflow-hidden flex flex-col items-center justify-center ring-1 ring-white/10">
                    {videoResultUrl ? (
                      <video
                        src={videoResultUrl}
                        controls
                        autoPlay
                        loop
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="p-6 text-center space-y-3">
                        <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center mx-auto border border-slate-800">
                          <Play className="w-8 h-8 text-indigo-400 ml-1" />
                        </div>
                        <h4 className="text-sm font-semibold text-white">Cinematic Widescreen Preview</h4>
                        <p className="text-xs text-slate-400">
                          16:9 Landscape format ready for YouTube and cinematic movie pipelines.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Download Button */}
                {videoResultUrl && (
                  <div className="mt-4 flex items-center space-x-3">
                    <a
                      href={videoResultUrl}
                      download
                      className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center space-x-2 shadow-lg shadow-emerald-600/20"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download Rendered MP4</span>
                    </a>
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

      </main>
    </div>
  );
}
