import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, Video, Film, Wand2, Play, RefreshCw, CheckCircle2, 
  AlertCircle, ChevronRight, Volume2, Smartphone, 
  Monitor, ArrowRight, Eye, ShieldCheck, Zap, Download, Layers, Flame,
  Activity, Clock, Server, Terminal, AlertTriangle, XCircle, Check, Info,
  Search, Sliders, ChevronDown, ChevronUp, Copy, CheckCheck,
  Key, ExternalLink, Lock
} from 'lucide-react';

const GENRES = [
  {
    id: "informative",
    label: "Informative & Science",
    description: "Macro details, laboratory aesthetics, high-curiosity documentary breakthroughs",
    icon: "🔬",
    accent: "from-blue-500/20 to-cyan-500/20 border-blue-500/40 text-blue-300"
  },
  {
    id: "mythology",
    label: "Mythology & Legends",
    description: "Epic volumetric lighting, ancient secrets, dramatic divine reveals",
    icon: "🏛️",
    accent: "from-amber-500/20 to-orange-500/20 border-amber-500/40 text-amber-300"
  },
  {
    id: "horror",
    label: "Dark Mystery & Noir",
    description: "Chiaroscuro shadows, classified files, eerie psychological hooks",
    icon: "🕵️",
    accent: "from-purple-500/20 to-indigo-500/20 border-purple-500/40 text-purple-300"
  },
  {
    id: "motivational",
    label: "Motivational & Energy",
    description: "Golden hour, uplifting narrative arcs, relentless drive and focus",
    icon: "⚡",
    accent: "from-emerald-500/20 to-teal-500/20 border-emerald-500/40 text-emerald-300"
  },
  {
    id: "thriller",
    label: "Thriller & True Crime",
    description: "Cold tones, tension-driven pacing, shocking suspense reveals",
    icon: "🚨",
    accent: "from-rose-500/20 to-red-500/20 border-rose-500/40 text-rose-300"
  },
  {
    id: "comedy",
    label: "Comedy & Satire",
    description: "Punchy pop pacing, exaggerated expressions, vibrant colorful chaos",
    icon: "😂",
    accent: "from-pink-500/20 to-rose-500/20 border-pink-500/40 text-pink-300"
  },
  {
    id: "scientific",
    label: "Scientific Deep Dive",
    description: "Precision, data-driven, crisp microscopic and anatomical clarity",
    icon: "🧬",
    accent: "from-cyan-500/20 to-sky-500/20 border-cyan-500/40 text-cyan-300"
  },
  {
    id: "sci_fi",
    label: "Sci-Fi & Cyberpunk",
    description: "Anamorphic neon flares, holographic tech, interstellar cosmic stakes",
    icon: "🚀",
    accent: "from-indigo-500/20 to-purple-500/20 border-indigo-500/40 text-indigo-300"
  }
];

const VOICES = [
  { id: "en-US-ChristopherNeural", name: "Christopher (US Documentary)", desc: "Authoritative, deep cinematic narration" },
  { id: "en-US-GuyNeural", name: "Guy (US Energetic & Fast)", desc: "Punchy, casual social media cadence" },
  { id: "en-US-JennyNeural", name: "Jenny (US Clear & Natural)", desc: "Engaging, crisp storytelling" },
  { id: "en-GB-RyanNeural", name: "Ryan (UK Classic)", desc: "Sophisticated lore, history, and mysteries" },
  { id: "en-AU-WilliamNeural", name: "William (AU Dynamic)", desc: "Grounded, modern narration pace" }
];

const EDIT_STYLES = [
  { id: "fast_cuts", label: "Fast Cuts (Viral)", desc: "8-12 cuts per 30s (1.5-2.5s/clip) — TikTok/Reels native pacing" },
  { id: "hybrid", label: "Hybrid", desc: "Fast hook opening -> medium build -> cinematic climax" },
  { id: "cinematic", label: "Cinematic", desc: "4-6 scenes, slow zoompan + motion blur, documentary feel" },
];

const SUBTITLE_STYLES = [
  { id: "hormozi_bold", label: "Hormozi Viral", desc: "Bold yellow & white uppercase with black stroke" },
  { id: "beast_color", label: "MrBeast Pop", desc: "High contrast green & yellow punch animation" },
  { id: "minimal_clean", label: "Clean Modern", desc: "Sleek Helvetica with soft drop shadow" },
  { id: "cinematic_noir", label: "Cinematic Noir", desc: "Gold serif italic with film elegance" },
];

const DEFAULT_VIDEO_ENGINES = [
  {
    id: "fast_motion",
    label: "Fast Motion Reel (2.5D)",
    engine: "FFmpeg Ken Burns Physics",
    description: "Instant render (~20s). High-res AI keyframes with cinematic camera zooms, pans, and whip cuts.",
    type: "2.5d_motion",
    speed: "~20s total",
    cost: "$0.00 / Free",
    is_available: true,
    badge: "Instant & Free",
    icon: "⚡",
  },
  {
    id: "gemini_omni",
    label: "Google Gemini Omni / Veo",
    engine: "gemini-omni-1.1-flash",
    description: "True generative AI video with native 9:16 vertical format, fluid motion, and image-to-video consistency.",
    type: "true_ai_video",
    speed: "~45-75s/scene",
    cost: "~$0.05-0.15/clip",
    is_available: true,
    requires: "Google Gemini Key",
    badge: "Cinema Motion",
    icon: "🎬",
  },
  {
    id: "minimax",
    label: "MiniMax Video-01 (Hailuo)",
    engine: "minimax/video-01 via Replicate",
    description: "Photorealistic human dynamics, expressive facial motion, dramatic cinematic camera moves.",
    type: "true_ai_video",
    speed: "~60s/scene",
    cost: "~$0.05/clip",
    is_available: false,
    requires: "Replicate Token",
    badge: "Best for Humans",
    icon: "🎥",
  },
  {
    id: "luma",
    label: "Luma Dream Machine (Ray)",
    engine: "luma/ray via Replicate",
    description: "Fluid natural physics, volumetric lighting, atmospheric environments, and smooth camera flights.",
    type: "true_ai_video",
    speed: "~45s/scene",
    cost: "~$0.10/clip",
    is_available: false,
    requires: "Replicate Token",
    badge: "Best for Physics",
    icon: "🌌",
  },
  {
    id: "hybrid",
    label: "Hybrid Cinema Reel",
    engine: "AI Video (Hook & Climax) + 2.5D Transitions",
    description: "True AI Video for Scene 1 (the vital 3s hook) and turning point, with fast 2.5D motion for transitions.",
    type: "hybrid",
    speed: "~1-2m total",
    cost: "~$0.10-0.20 total",
    is_available: true,
    badge: "Recommended",
    icon: "🎭",
  },
];

export default function App() {
  // Navigation
  const [activeStep, setActiveStep] = useState(1);
  
  // Generation inputs
  const [topic, setTopic] = useState("Roman Self-Healing Concrete");
  const [genre, setGenre] = useState("informative");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [editStyle, setEditStyle] = useState("fast_cuts");
  const [selectedVoice, setSelectedVoice] = useState("en-US-ChristopherNeural");
  const [subtitleStyle, setSubtitleStyle] = useState("hormozi_bold");
  const [videoEngineMode, setVideoEngineMode] = useState("hybrid");
  const [videoEngines, setVideoEngines] = useState(DEFAULT_VIDEO_ENGINES);
  const [enableResearch, setEnableResearch] = useState(false);
  
  // Provider health & status
  const [providers, setProviders] = useState(null);
  
  // State for LangGraph Hook Engine
  const [isGeneratingHooks, setIsGeneratingHooks] = useState(false);
  const [hookData, setHookData] = useState(null);
  const [selectedHook, setSelectedHook] = useState(null);
  
  // State for Script Storyboard
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [scriptData, setScriptData] = useState(null);
  
  // Video Rendering State
  const [isRendering, setIsRendering] = useState(false);
  const [renderJob, setRenderJob] = useState(null);
  const [renderProgress, setRenderProgress] = useState(0);
  const [renderStage, setRenderStage] = useState("");
  const [renderStatusText, setRenderStatusText] = useState("");
  const [renderLogs, setRenderLogs] = useState([]);
  const [videoResultUrl, setVideoResultUrl] = useState(null);
  
  // Active Progress & Live HUD State
  const [activeTaskName, setActiveTaskName] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [liveSteps, setLiveSteps] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [showLogsDrawer, setShowLogsDrawer] = useState(false);
  const [activityLogs, setActivityLogs] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [copiedLog, setCopiedLog] = useState(false);

  // Settings & Paid API Keys State
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsKeys, setSettingsKeys] = useState(null);
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [openaiKeyInput, setOpenaiKeyInput] = useState('');
  const [elevenlabsKeyInput, setElevenlabsKeyInput] = useState('');
  const [replicateTokenInput, setReplicateTokenInput] = useState('');
  const [deepResearchToggle, setDeepResearchToggle] = useState(false);
  const [isSavingKeys, setIsSavingKeys] = useState(false);
  const [settingsStatusMsg, setSettingsStatusMsg] = useState(null);

  const timerRef = useRef(null);

  // Suggestions
  const topicSuggestions = [
    "Neem Karoli Baba: The Mystic of Kainchi Dham",
    "Roman Self-Healing Concrete",
    "The Voynich Manuscript",
    "Why Samurai Used Incense Clocks",
    "What If Earth Stopped Spinning for 1 Second?",
    "The Secret Psychology of Casinos",
    "Antikythera Mechanism: Ancient Computer"
  ];

  // Fetch active providers & settings on load
  useEffect(() => {
    fetchProviders();
    fetchSettingsKeys();
    fetchPresets();
  }, []);

  const fetchPresets = async () => {
    try {
      const res = await fetch('/api/presets');
      if (res.ok) {
        const data = await res.json();
        if (data.video_engines && data.video_engines.length > 0) {
          setVideoEngines(data.video_engines);
        }
      }
    } catch (e) {
      console.warn("Could not fetch presets:", e);
    }
  };

  const fetchProviders = async () => {
    try {
      const res = await fetch('/api/providers');
      if (res.ok) {
        const data = await res.json();
        setProviders(data);
        addLog(`System initialized. LLM: ${data.llm.provider}, Image: ${data.image.provider}, TTS: ${data.tts.provider}`);
      }
    } catch (e) {
      console.warn("Could not fetch provider status:", e);
    }
  };

  const fetchSettingsKeys = async () => {
    try {
      const res = await fetch('/api/settings/keys');
      if (res.ok) {
        const data = await res.json();
        setSettingsKeys(data);
        setDeepResearchToggle(data.deep_research_enabled || false);
        if (data.providers) {
          setProviders(data.providers);
        }
      }
    } catch (e) {
      console.warn("Could not fetch settings keys:", e);
    }
  };

  const handleSaveKeys = async () => {
    setIsSavingKeys(true);
    setSettingsStatusMsg(null);
    try {
      const payload = {
        deep_research_enabled: deepResearchToggle,
      };
      if (geminiKeyInput.trim()) payload.gemini_api_key = geminiKeyInput.trim();
      if (openaiKeyInput.trim()) payload.openai_api_key = openaiKeyInput.trim();
      if (elevenlabsKeyInput.trim()) payload.elevenlabs_api_key = elevenlabsKeyInput.trim();
      if (replicateTokenInput.trim()) payload.replicate_api_token = replicateTokenInput.trim();

      const res = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setSettingsStatusMsg({ type: 'success', text: 'AI Keys saved! Models hot-reloaded successfully.' });
        addLog(`Settings updated: LLM=${data.providers?.llm?.provider}, Img=${data.providers?.image?.provider}, TTS=${data.providers?.tts?.provider}`);
        setGeminiKeyInput('');
        setOpenaiKeyInput('');
        setElevenlabsKeyInput('');
        setReplicateTokenInput('');
        fetchSettingsKeys();
        fetchProviders();
      } else {
        setSettingsStatusMsg({ type: 'error', text: data.detail || 'Failed to save settings' });
      }
    } catch (err) {
      setSettingsStatusMsg({ type: 'error', text: err.message || 'Network error saving settings' });
    } finally {
      setIsSavingKeys(false);
    }
  };

  const addLog = (msg) => {
    const timestamp = new Date().toLocaleTimeString();
    setActivityLogs(prev => [`[${timestamp}] ${msg}`, ...prev.slice(0, 49)]);
  };

  // Timer helper for progress
  const startTimer = (taskName, steps) => {
    setErrorMessage(null);
    setActiveTaskName(taskName);
    setLiveSteps(steps);
    setCurrentStepIndex(0);
    setElapsedSeconds(0);
    clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsedSeconds(s => s + 1);
    }, 1000);
  };

  const stopTimer = () => {
    clearInterval(timerRef.current);
    setActiveTaskName(null);
  };

  // 1. Generate & Verify Viral Hooks
  const handleGenerateHooks = async () => {
    setIsGeneratingHooks(true);
    setHookData(null);
    setSelectedHook(null);
    setErrorMessage(null);

    const steps = [
      "Analyzing topic & narrative genre parameters...",
      "Synthesizing 5 high-retention hook archetypes...",
      "Running LangGraph adversarial critic evaluation...",
      "Verifying curiosity gaps and scroll-stopping cadence..."
    ];
    startTimer("Generating & Verifying Viral Hooks", steps);
    addLog(`Initiated hook formulation for topic: "${topic}" (${genre})`);

    // Advance steps visually while waiting
    const stepInterval = setInterval(() => {
      setCurrentStepIndex(i => Math.min(i + 1, steps.length - 1));
    }, 1200);

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

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errJson.detail || `Server error (${res.status})`);
      }

      const data = await res.json();
      setHookData(data);
      if (data.winning_hook) {
        setSelectedHook(data.winning_hook);
      }
      addLog(`Hook generation complete! Evaluated ${data.all_iterations?.length || 1} iteration(s). Winning score: ${data.winning_evaluation?.total_score || 85}/100.`);
    } catch (err) {
      console.error("Hook generation failed:", err);
      const errMsg = err.message || "Failed to generate hooks";
      setErrorMessage({
        title: "Hook Generation Failed",
        detail: errMsg,
        action: "Please check that the server is running. You can click 'Retry' to run with fallback mode."
      });
      addLog(`ERROR: ${errMsg}`);
    } finally {
      clearInterval(stepInterval);
      stopTimer();
      setIsGeneratingHooks(false);
    }
  };

  // 2. Generate Scene Script
  const handleGenerateScript = async () => {
    setIsGeneratingScript(true);
    setErrorMessage(null);

    const steps = [
      "Structuring viral retention curve & pacing formula...",
      "Writing punchy scene-by-scene voiceover narration...",
      "Generating cinematic visual prompts & camera motions...",
      "Optimizing visual style descriptors for AI generators..."
    ];
    startTimer("Writing Micro-Scene Storyboard", steps);
    addLog(`Generating script for "${topic}" using hook: "${selectedHook?.text || 'Default'}"`);

    const stepInterval = setInterval(() => {
      setCurrentStepIndex(i => Math.min(i + 1, steps.length - 1));
    }, 1000);

    try {
      const res = await fetch('/api/scripts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          genre,
          aspect_ratio: aspectRatio,
          target_duration_sec: 30,
          edit_style: editStyle,
          enable_research: enableResearch,
          selected_hook: selectedHook
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errJson.detail || `Server error (${res.status})`);
      }

      const data = await res.json();
      setScriptData(data);
      addLog(`Storyboard assembled with ${data.scenes?.length || 0} scenes (~${data.estimated_total_duration || 30}s).`);
      setActiveStep(2);
    } catch (err) {
      console.error("Script generation failed:", err);
      const errMsg = err.message || "Failed to generate script";
      setErrorMessage({
        title: "Script Generation Failed",
        detail: errMsg,
        action: "Check the backend connection and try again."
      });
      addLog(`ERROR: ${errMsg}`);
    } finally {
      clearInterval(stepInterval);
      stopTimer();
      setIsGeneratingScript(false);
    }
  };

  // 3. Trigger Video Render & Track Progress
  const handleStartRender = async () => {
    if (!scriptData) return;
    setIsRendering(true);
    setRenderProgress(5);
    setRenderStage("queued");
    setRenderStatusText("Initializing Production Pipeline...");
    setRenderLogs(["Job initialized and queued..."]);
    setErrorMessage(null);
    setVideoResultUrl(null);

    const steps = [
      "Synthesizing neural voiceover narration with Edge-TTS...",
      "Generating high-resolution AI visuals & sub-clip variations...",
      "Compositing camera zooms, pans, and cinematic motion...",
      "Ducking and mixing background music soundtrack...",
      "Burning dynamic Hormozi-style subtitle typography...",
      "Exporting final high-definition MP4..."
    ];
    startTimer("Rendering Final MP4 Video", steps);
    addLog(`Initiating render job for ${scriptData.scenes?.length} scenes, voice: ${selectedVoice}, style: ${subtitleStyle}`);

    try {
      const res = await fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script: scriptData,
          voice_name: selectedVoice,
          subtitle_style: subtitleStyle,
          aspect_ratio: aspectRatio,
          include_bg_music: true,
          bg_music_genre: genre,
          video_engine_mode: videoEngineMode
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errJson.detail || `Render initiation failed (${res.status})`);
      }

      const data = await res.json();
      setRenderJob(data);
      addLog(`Render job #${data.job_id} accepted. Polling status...`);

      // Poll status
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/video/status/${data.job_id}`);
          if (!statusRes.ok) return;
          const statusData = await statusRes.json();
          
          setRenderProgress(statusData.progress_percent || 10);
          setRenderStage(statusData.stage || statusData.status);
          if (statusData.stage_message) {
            setRenderStatusText(statusData.stage_message);
          }
          if (statusData.logs && statusData.logs.length > 0) {
            setRenderLogs(statusData.logs);
            const latestLog = statusData.logs[statusData.logs.length - 1];
            addLog(`[Job #${data.job_id}] ${latestLog}`);
          }

          // Map stage to step index
          if (statusData.status === "generating_voiceover") setCurrentStepIndex(0);
          else if (statusData.status === "generating_visuals") setCurrentStepIndex(1);
          else if (statusData.status === "compositing_video") setCurrentStepIndex(2);
          else if (statusData.status === "burning_subtitles") setCurrentStepIndex(4);

          if (statusData.status === "completed") {
            clearInterval(pollInterval);
            setIsRendering(false);
            stopTimer();
            setRenderProgress(100);
            setRenderStatusText("Video Generated Successfully!");
            setVideoResultUrl(statusData.video_url);
            addLog(`SUCCESS: Video #${data.job_id} is ready at ${statusData.video_url}`);
          } else if (statusData.status === "failed") {
            clearInterval(pollInterval);
            setIsRendering(false);
            stopTimer();
            const errMsg = statusData.error_message || "Video rendering encountered an error";
            setRenderStatusText(`Render Failed: ${errMsg}`);
            setErrorMessage({
              title: "Video Rendering Failed",
              detail: errMsg,
              action: "Please verify FFmpeg and audio assets are available. You can re-render anytime."
            });
            addLog(`ERROR: Render job #${data.job_id} failed: ${errMsg}`);
          }
        } catch (e) {
          console.warn("Poll error:", e);
        }
      }, 1500);
    } catch (err) {
      console.error("Render request failed:", err);
      const errMsg = err.message || "Render request failed";
      setErrorMessage({
        title: "Could Not Start Render",
        detail: errMsg,
        action: "Ensure the backend server is reachable at http://127.0.0.1:8000"
      });
      addLog(`ERROR: ${errMsg}`);
      setIsRendering(false);
      stopTimer();
    }
  };

  const copyLogs = () => {
    navigator.clipboard.writeText(activityLogs.join('\n'));
    setCopiedLog(true);
    setTimeout(() => setCopiedLog(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* TOP HEADER */}
      <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Film className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">CineShorts AI</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-medium">
                  v2.0 Production
                </span>
              </div>
              <p className="text-xs text-slate-400">Agentic Viral Video Production Studio</p>
            </div>
          </div>

          {/* Right Header: Provider Status & Activity Button */}
          <div className="flex items-center space-x-3">
            {/* AI Models & API Keys Settings Button */}
            <button
              onClick={() => {
                fetchSettingsKeys();
                setShowSettingsModal(true);
              }}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-indigo-500/40 bg-gradient-to-r from-indigo-500/15 to-purple-500/15 hover:from-indigo-500/25 hover:to-purple-500/25 text-indigo-200 hover:text-white transition-all text-xs font-semibold shadow-sm"
              title="Configure paid models for production quality"
            >
              <Sliders className="w-3.5 h-3.5 text-indigo-400" />
              <span>AI Models & Keys</span>
              {settingsKeys?.has_gemini_api_key ? (
                <span className="flex items-center space-x-1 bg-emerald-500/20 text-emerald-300 text-[10px] px-1.5 py-0.5 rounded-md border border-emerald-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Gemini 2.5 Pro</span>
                </span>
              ) : (
                <span className="text-[10px] text-amber-300 bg-amber-500/15 px-1.5 py-0.5 rounded-md border border-amber-500/30">
                  Free / Grounded
                </span>
              )}
            </button>

            {providers && (
              <div className="hidden md:flex items-center space-x-2 bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
                <div className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-slate-400">LLM:</span>
                  <span className="font-semibold text-slate-200 capitalize">{providers.llm.provider}</span>
                </div>
                <span className="text-slate-700">|</span>
                <div className="flex items-center space-x-1">
                  <span className="text-slate-400">Img:</span>
                  <span className="font-semibold text-slate-200 capitalize">{providers.image.provider}</span>
                </div>
                <span className="text-slate-700">|</span>
                <div className="flex items-center space-x-1">
                  <span className="text-slate-400">TTS:</span>
                  <span className="font-semibold text-slate-200 capitalize">{providers.tts.provider}</span>
                </div>
              </div>
            )}

            {/* Toggle Activity Logs Drawer */}
            <button
              onClick={() => setShowLogsDrawer(!showLogsDrawer)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
                showLogsDrawer
                  ? "bg-indigo-600 text-white border-indigo-500 shadow"
                  : "bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Live Console</span>
              {activityLogs.length > 0 && (
                <span className="w-2 h-2 rounded-full bg-emerald-400 ml-1" />
              )}
            </button>

            {/* Format Selector */}
            <div className="bg-slate-800/80 p-1 rounded-xl border border-slate-700/60 flex items-center space-x-1">
              <button
                onClick={() => setAspectRatio("9:16")}
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  aspectRatio === "9:16" 
                    ? "bg-indigo-600 text-white shadow" 
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Smartphone className="w-3.5 h-3.5" />
                <span>9:16 Shorts</span>
              </button>
              <button
                onClick={() => setAspectRatio("16:9")}
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  aspectRatio === "16:9" 
                    ? "bg-indigo-600 text-white shadow" 
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Monitor className="w-3.5 h-3.5" />
                <span>16:9 Cinema</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* STEPPER NAVIGATION */}
      <div className="border-b border-slate-800 bg-slate-900/30 py-3 sticky top-16 z-40 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-4 flex items-center justify-between">
          <button 
            onClick={() => setActiveStep(1)}
            className={`flex items-center space-x-2 text-sm font-medium transition-colors ${
              activeStep === 1 ? "text-indigo-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              activeStep === 1 ? "bg-indigo-500 text-white ring-4 ring-indigo-500/20" : "bg-slate-800 text-slate-400"
            }`}>1</span>
            <span>1. Hook Formulation & Critic</span>
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
              activeStep === 2 ? "bg-indigo-500 text-white ring-4 ring-indigo-500/20" : "bg-slate-800 text-slate-400"
            }`}>2</span>
            <span>2. Scene Director Storyboard</span>
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
              activeStep === 3 ? "bg-indigo-500 text-white ring-4 ring-indigo-500/20" : "bg-slate-800 text-slate-400"
            }`}>3</span>
            <span>3. Studio Video Compositor</span>
          </button>
        </div>
      </div>

      {/* ACTIVE GLOBAL PROGRESS & HUD BANNER */}
      {(activeTaskName || isGeneratingHooks || isGeneratingScript || isRendering) && (
        <div className="bg-gradient-to-r from-indigo-950/90 via-purple-950/90 to-slate-950/90 border-b border-indigo-500/30 p-4 shadow-2xl backdrop-blur-md sticky top-28 z-30 animate-in slide-in-from-top-4 duration-300">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center space-x-3.5">
              <div className="relative">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center">
                  <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
                </div>
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
                </span>
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h4 className="font-bold text-sm text-white">{activeTaskName || "Processing Pipeline Step..."}</h4>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/30 border border-indigo-400/40 text-indigo-200 font-mono flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{String(Math.floor(elapsedSeconds / 60)).padStart(2, '0')}:{String(elapsedSeconds % 60).padStart(2, '0')}</span>
                  </span>
                </div>
                <p className="text-xs text-indigo-200/80 mt-0.5 flex items-center space-x-1.5">
                  <Activity className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
                  <span>{liveSteps[currentStepIndex] || renderStatusText || "Engine active and synthesizing assets..."}</span>
                </p>
              </div>
            </div>

            {/* Stepper Dots */}
            {liveSteps.length > 0 && (
              <div className="flex items-center space-x-2">
                {liveSteps.map((s, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center space-x-1 text-xs px-2.5 py-1 rounded-lg border transition-all ${
                      idx === currentStepIndex
                        ? "bg-indigo-600 text-white border-indigo-400 font-bold shadow-lg shadow-indigo-500/20 scale-105"
                        : idx < currentStepIndex
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30 font-medium"
                        : "bg-slate-900/60 text-slate-500 border-slate-800"
                    }`}
                  >
                    {idx < currentStepIndex ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <span className="font-mono text-[10px]">{idx + 1}</span>
                    )}
                    <span className="hidden lg:inline">{s.split(" ")[0]}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ERROR BANNER / DIAGNOSTICS */}
      {errorMessage && (
        <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-4">
          <div className="bg-rose-950/40 border-2 border-rose-500/50 rounded-2xl p-5 shadow-2xl backdrop-blur-md animate-in shake duration-300">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3.5">
                <AlertTriangle className="w-6 h-6 text-rose-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-base text-rose-200">{errorMessage.title}</h3>
                  <p className="text-xs font-mono text-rose-300/90 mt-1 bg-rose-950/70 p-2.5 rounded-lg border border-rose-800/60 select-all">
                    {errorMessage.detail}
                  </p>
                  <p className="text-xs text-rose-200/80 mt-2 flex items-center space-x-1">
                    <Info className="w-3.5 h-3.5 text-rose-400" />
                    <span>{errorMessage.action}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setErrorMessage(null)}
                className="p-1 rounded-lg text-rose-400 hover:bg-rose-900/50 transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* STEP 1: HOOK FORMULATION & CRITIC */}
        {activeStep === 1 && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Topic & Strategy Card */}
            <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                  <Flame className="w-5 h-5 text-amber-400" />
                  <span>Topic & Viral Angle Formulation</span>
                </h2>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-400">Edit Pacing:</span>
                  <select
                    value={editStyle}
                    onChange={(e) => setEditStyle(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-xs rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    {EDIT_STYLES.map(s => (
                      <option key={s.id} value={s.id}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Topic Input */}
              <div className="space-y-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>Video Concept / Core Story Idea</span>
                  <span className="text-[11px] text-indigo-400">Fast multi-cut engine active</span>
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
                  <span className="text-xs text-slate-500 self-center">Trending prompts:</span>
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
              <div className="space-y-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Select Visual & Narrative Genre
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {GENRES.map((g) => {
                    const isSelected = genre === g.id;
                    return (
                      <button
                        key={g.id}
                        onClick={() => setGenre(g.id)}
                        className={`text-left p-3.5 rounded-xl border transition-all relative overflow-hidden flex flex-col justify-between ${
                          isSelected
                            ? `bg-gradient-to-b ${g.accent} shadow-lg ring-1 ring-white/20`
                            : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/50"
                        }`}
                      >
                        <div>
                          <div className="text-2xl mb-1.5">{g.icon}</div>
                          <h3 className="font-semibold text-sm text-white">{g.label}</h3>
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{g.description}</p>
                        </div>
                        {isSelected && (
                          <div className="mt-2.5 flex items-center space-x-1 text-[11px] font-medium text-white/90">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Selected</span>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action Bar */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-800/80">
                <div className="flex items-center space-x-3 text-xs text-slate-400">
                  <span className="flex items-center space-x-1">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Adversarial Critic Loop</span>
                  </span>
                  <span>•</span>
                  <span>Target Pass: 80/100</span>
                </div>

                <button
                  onClick={handleGenerateHooks}
                  disabled={isGeneratingHooks || !topic.trim()}
                  className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 hover:from-indigo-400 hover:to-pink-400 text-white font-bold text-sm flex items-center justify-center space-x-2 shadow-xl shadow-indigo-500/25 transition-all disabled:opacity-50"
                >
                  {isGeneratingHooks ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Synthesizing ({elapsedSeconds}s)...</span>
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

            {/* HOOK RESULTS & ADVERSARIAL CRITIC EVALUATION */}
            {hookData && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <span>LangGraph Adversarial Critic Analysis</span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Evaluated {hookData.total_iterations} Iteration(s) | Passing Threshold: 80/100
                    </p>
                  </div>
                </div>

                {/* Candidate Hook Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {hookData.all_iterations?.[hookData.all_iterations.length - 1]?.candidates?.map((cand) => {
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
                            ? "bg-slate-900 border-indigo-500 shadow-xl shadow-indigo-500/20 ring-2 ring-indigo-500/50"
                            : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90"
                        }`}
                      >
                        <div>
                          {/* Header badges */}
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-indigo-300 border border-slate-700">
                              {cand.archetype.replace('_', ' ')}
                            </span>
                            <div className={`flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                              passed ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            }`}>
                              <span>{score}/100</span>
                            </div>
                          </div>

                          {/* Hook Spoken Text */}
                          <p className="font-bold text-white text-base leading-snug mb-3">
                            "{cand.text}"
                          </p>

                          {/* Visual Concept */}
                          <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800/80 mb-3 text-xs space-y-1">
                            <div className="text-slate-400 font-medium flex items-center space-x-1">
                              <Eye className="w-3.5 h-3.5 text-indigo-400" />
                              <span>0-2s Visual Metaphor:</span>
                            </div>
                            <p className="text-slate-300 italic">{cand.visual_concept}</p>
                          </div>

                          {/* Audio SFX */}
                          <div className="flex items-center space-x-2 text-xs text-slate-400">
                            <Volume2 className="w-3.5 h-3.5 text-pink-400" />
                            <span>SFX Cue: <code className="text-pink-300 font-mono">{cand.audio_sfx_cue}</code></span>
                          </div>
                        </div>

                        {/* Breakdown Radar Pill */}
                        <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-1.5">
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Retention Pull:</span>
                            <span className="font-medium text-slate-200">{evalObj?.retention_pull_score || 25}/30</span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Curiosity Gap:</span>
                            <span className="font-medium text-slate-200">{evalObj?.curiosity_index_score || 21}/25</span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Visual Execution:</span>
                            <span className="font-medium text-slate-200">{evalObj?.visual_potential_score || 23}/25</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Critic Consensus Action Banner */}
                {hookData.winning_evaluation && (
                  <div className="bg-gradient-to-r from-slate-900 to-indigo-950/60 border border-indigo-500/40 rounded-2xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        <span className="font-bold text-white">Verifier Consensus: Hook Ready for Production</span>
                      </div>
                      <p className="text-xs text-slate-300 max-w-2xl">
                        {hookData.winning_evaluation.strengths?.[0] || "Hook achieves high initial retention and cognitive curiosity without preamble."}
                      </p>
                    </div>

                    <button
                      onClick={handleGenerateScript}
                      disabled={isGeneratingScript || !selectedHook}
                      className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm flex items-center space-x-2 shadow-lg shadow-indigo-600/30 whitespace-nowrap transition-all"
                    >
                      {isGeneratingScript ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Generating Micro-Scenes ({elapsedSeconds}s)...</span>
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
                  Total Duration: ~{scriptData.estimated_total_duration}s | Pacing: {scriptData.edit_style || editStyle} | Scenes: {scriptData.scenes?.length}
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setActiveStep(1)}
                  className="px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-xs font-medium text-slate-300"
                >
                  Edit Hook
                </button>
                <button
                  onClick={() => setActiveStep(3)}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-sm flex items-center space-x-2 shadow-lg shadow-indigo-500/25"
                >
                  <span>Proceed to Studio Production</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Scenes Timeline */}
            <div className="space-y-4">
              {scriptData.scenes?.map((sc, idx) => (
                <div
                  key={sc.scene_id || idx}
                  className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-all flex flex-col lg:flex-row gap-6"
                >
                  {/* Scene Badge & Camera */}
                  <div className="w-full lg:w-48 flex-shrink-0 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-slate-800 pb-4 lg:pb-0 lg:pr-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="px-2.5 py-0.5 rounded-lg bg-indigo-500/20 text-indigo-300 font-bold text-xs border border-indigo-500/30">
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
                          <span className="capitalize">{sc.camera_motion?.replace('_', ' ') || "Zoom In"}</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3">
                      <span className="text-[11px] text-slate-500 uppercase font-medium">Audio SFX Cue</span>
                      <div className="text-xs text-pink-300 font-mono mt-0.5">
                        {sc.audio_sfx_cue || "whoosh"}
                      </div>
                    </div>
                  </div>

                  {/* Scene Voiceover and Visual Prompts */}
                  <div className="flex-1 space-y-3">
                    {/* Voiceover */}
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1 mb-1">
                        <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Spoken Narration ({sc.duration_sec}s)</span>
                      </label>
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
                          <span>AI Visual Prompt</span>
                        </label>
                        <span className="text-[11px] text-indigo-400 font-medium">{sc.visual_hook_type || "Hard Cut"}</span>
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

                  {/* On-screen Callout Overlay */}
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

            {/* Retention Loop */}
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-xl p-4 flex items-center justify-between">
              <span className="text-xs text-slate-400">Retention Call to Action:</span>
              <span className="text-xs font-semibold text-indigo-300">"{scriptData.call_to_action}"</span>
            </div>
          </div>
        )}

        {/* STEP 3: STUDIO PRODUCTION & RENDER */}
        {activeStep === 3 && scriptData && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Left Column: Settings */}
              <div className="lg:col-span-6 space-y-6">
                <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
                  <div>
                    <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                      <Video className="w-5 h-5 text-indigo-400" />
                      <span>Studio Compositor Engine</span>
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">Multi-cut assembly, neural speech synthesis & subtitle burning</p>
                  </div>

                  {/* Voice Selector */}
                  <div className="space-y-3">
                    <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Narrator Neural Voice (Edge-TTS)
                    </label>
                    <div className="space-y-2">
                      {VOICES.map((v) => (
                        <div
                          key={v.id}
                          onClick={() => setSelectedVoice(v.id)}
                          className={`cursor-pointer p-3 rounded-xl border transition-all flex items-center justify-between ${
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
                      {SUBTITLE_STYLES.map((st) => (
                        <button
                          key={st.id}
                          onClick={() => setSubtitleStyle(st.id)}
                          className={`p-3 rounded-xl border text-left transition-all ${
                            subtitleStyle === st.id
                              ? "bg-indigo-600/20 border-indigo-400 text-indigo-200 shadow"
                              : "bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700"
                          }`}
                        >
                          <div className="font-bold text-xs uppercase tracking-wider">{st.label}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5">{st.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* AI Video Engine & Motion Model */}
                  <div className="space-y-3 pt-2">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                        <Video className="w-4 h-4 text-pink-400" />
                        <span>AI Video Generation Engine</span>
                      </label>
                      <span className="text-[11px] text-slate-500">True AI Video or 2.5D Fast Motion</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {videoEngines.map((eng) => {
                        const isSelected = videoEngineMode === eng.id;
                        return (
                          <button
                            key={eng.id}
                            type="button"
                            onClick={() => setVideoEngineMode(eng.id)}
                            className={`p-3.5 rounded-xl border text-left transition-all relative ${
                              isSelected
                                ? "bg-gradient-to-br from-pink-500/15 via-purple-500/10 to-transparent border-pink-400 text-slate-100 shadow-lg shadow-pink-500/10"
                                : "bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex justify-between items-start">
                              <div className="font-bold text-xs flex items-center space-x-1.5">
                                <span>{eng.icon || "🎬"}</span>
                                <span>{eng.label}</span>
                              </div>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                eng.badge === "Instant & Free" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" :
                                eng.badge === "Recommended" ? "bg-purple-500/20 text-purple-300 border border-purple-500/30" :
                                eng.is_available ? "bg-blue-500/20 text-blue-300 border border-blue-500/30" :
                                "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              }`}>
                                {eng.badge}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                              {eng.description}
                            </div>
                            <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                              <span>⏱️ {eng.speed}</span>
                              <span>💳 {eng.cost}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Render Button */}
                  <div className="pt-2">
                    <button
                      onClick={handleStartRender}
                      disabled={isRendering}
                      className="w-full py-4 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 hover:from-indigo-400 hover:to-pink-400 text-white font-bold text-sm flex items-center justify-center space-x-2 shadow-xl shadow-purple-500/20 transition-all disabled:opacity-50"
                    >
                      {isRendering ? (
                        <>
                          <RefreshCw className="w-5 h-5 animate-spin" />
                          <span>Rendering MP4 ({elapsedSeconds}s | {renderProgress}%)...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5 text-amber-300" />
                          <span>Render Final MP4 Video</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Real-time Render Progress Card */}
                  {isRendering && (
                    <div className="space-y-3 bg-slate-950/90 p-4 rounded-xl border border-indigo-500/30">
                      <div className="flex justify-between items-center text-xs font-semibold">
                        <span className="text-indigo-300 flex items-center space-x-1.5">
                          <Activity className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                          <span>{renderStatusText}</span>
                        </span>
                        <span className="text-indigo-400 font-mono text-sm">{renderProgress}%</span>
                      </div>
                      
                      {/* Bar */}
                      <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-full transition-all duration-500 rounded-full"
                          style={{ width: `${renderProgress}%` }}
                        />
                      </div>

                      {/* Live Logs Sub-box */}
                      {renderLogs.length > 0 && (
                        <div className="bg-black/80 rounded-lg p-2.5 border border-slate-800/80 text-[11px] font-mono text-slate-400 max-h-24 overflow-y-auto space-y-1">
                          {renderLogs.map((log, i) => (
                            <div key={i} className="flex items-start space-x-1.5">
                              <span className="text-indigo-500">›</span>
                              <span>{log}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Video Mockup */}
              <div className="lg:col-span-6 flex flex-col items-center justify-center">
                {aspectRatio === "9:16" ? (
                  <div className="relative w-full max-w-[340px] aspect-[9/16] bg-black rounded-[40px] border-4 border-slate-700/80 shadow-2xl overflow-hidden flex flex-col items-center justify-center ring-1 ring-white/10">
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
                          Click "Render Final MP4 Video" to synthesize multi-cut scenes, dynamic camera moves, and burned subtitle typography.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
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
                          16:9 Landscape format ready for YouTube long-form pipelines.
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
                      className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center space-x-2 shadow-lg shadow-emerald-600/25"
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

      {/* LIVE ACTIVITY CONSOLE DRAWER */}
      {showLogsDrawer && (
        <div className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/95 border-t border-slate-800 shadow-2xl backdrop-blur-xl animate-in slide-in-from-bottom-6 duration-300">
          <div className="max-w-7xl mx-auto p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <span className="text-sm font-bold text-white">Live System Console & Event Stream</span>
                <span className="text-xs text-slate-500">({activityLogs.length} events logged)</span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={copyLogs}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center space-x-1"
                >
                  {copiedLog ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedLog ? "Copied" : "Copy Log"}</span>
                </button>
                <button
                  onClick={() => setShowLogsDrawer(false)}
                  className="p-1 text-slate-400 hover:text-white rounded-lg"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="bg-black/90 rounded-xl p-3.5 border border-slate-800 text-xs font-mono text-slate-300 h-44 overflow-y-auto space-y-1.5">
              {activityLogs.length === 0 ? (
                <div className="text-slate-500 italic">No events logged yet. Actions will appear here in real-time.</div>
              ) : (
                activityLogs.map((log, i) => (
                  <div key={i} className={`flex items-start space-x-2 ${log.includes("ERROR") ? "text-rose-400" : log.includes("SUCCESS") ? "text-emerald-400" : ""}`}>
                    <span className="text-indigo-500 flex-shrink-0">›</span>
                    <span className="break-all">{log}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* SETTINGS & API KEYS MODAL */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl max-w-2xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                    <Sliders className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-lg text-white">AI Models & Production Keys</h3>
                </div>
                <p className="text-xs text-slate-400">
                  Ground scripts in real facts, upgrade to Gemini 2.5 Pro, and enable ultra-realistic voice narration.
                </p>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {settingsStatusMsg && (
              <div className={`p-3 rounded-xl text-xs flex items-center space-x-2 border ${
                settingsStatusMsg.type === 'success' 
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' 
                  : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
              }`}>
                {settingsStatusMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : <AlertTriangle className="w-4 h-4 flex-shrink-0" />}
                <span>{settingsStatusMsg.text}</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              {/* GEMINI API KEY */}
              <div className="p-4 rounded-xl bg-slate-950/70 border border-indigo-500/30 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Key className="w-4 h-4 text-indigo-400" />
                    <span className="font-bold text-white text-sm">Google Gemini API Key</span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold">
                      Recommended
                    </span>
                  </div>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 font-semibold text-[11px] underline"
                  >
                    <span>Get Key (Free & Paid)</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Powers <strong>Gemini 2.5 Pro</strong> scriptwriting, live Search fact grounding, Imagen 4K imagery, and <strong>Google Gemini Omni / Veo</strong> AI Video generation.
                </p>
                <div className="relative">
                  <input
                    type="password"
                    value={geminiKeyInput}
                    onChange={(e) => setGeminiKeyInput(e.target.value)}
                    placeholder={settingsKeys?.has_gemini_api_key ? `Connected (${settingsKeys.gemini_api_key_masked}) — Paste new key to update` : "Paste AIzaSy... API key here"}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono text-xs"
                  />
                </div>
              </div>

              {/* ELEVENLABS API KEY */}
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Volume2 className="w-4 h-4 text-purple-400" />
                    <span className="font-bold text-white text-sm">ElevenLabs API Key</span>
                    <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] font-semibold">
                      Ultra Voiceover
                    </span>
                  </div>
                  <a
                    href="https://elevenlabs.io"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-purple-400 hover:text-purple-300 font-semibold text-[11px] underline"
                  >
                    <span>elevenlabs.io</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Generates hyper-realistic human voiceover narration with emotions and documentary pacing. (Falls back to Edge-TTS if empty).
                </p>
                <input
                  type="password"
                  value={elevenlabsKeyInput}
                  onChange={(e) => setElevenlabsKeyInput(e.target.value)}
                  placeholder={settingsKeys?.has_elevenlabs_api_key ? `Connected (${settingsKeys.elevenlabs_api_key_masked}) — Paste new key to update` : "Paste ElevenLabs API key"}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono text-xs"
                />
              </div>

              {/* OPENAI API KEY */}
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span className="font-bold text-white text-sm">OpenAI API Key (GPT-4o)</span>
                  </div>
                  <a
                    href="https://platform.openai.com/api-keys"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-emerald-400 hover:text-emerald-300 font-semibold text-[11px] underline"
                  >
                    <span>platform.openai.com</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <input
                  type="password"
                  value={openaiKeyInput}
                  onChange={(e) => setOpenaiKeyInput(e.target.value)}
                  placeholder={settingsKeys?.has_openai_api_key ? `Connected (${settingsKeys.openai_api_key_masked}) — Paste new key to update` : "Paste sk-... API key"}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                />
              </div>

              {/* REPLICATE API TOKEN */}
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-amber-400" />
                    <span className="font-bold text-white text-sm">Replicate API Token (Flux & AI Video)</span>
                  </div>
                  <a
                    href="https://replicate.com/account/api-tokens"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-amber-400 hover:text-amber-300 font-semibold text-[11px] underline"
                  >
                    <span>replicate.com</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Powers <strong>Flux 1.1 Pro</strong> images, <strong>MiniMax Video-01</strong> (human realism), and <strong>Luma Ray</strong> (physics/environments).
                </p>
                <input
                  type="password"
                  value={replicateTokenInput}
                  onChange={(e) => setReplicateTokenInput(e.target.value)}
                  placeholder={settingsKeys?.has_replicate_api_token ? `Connected (${settingsKeys.replicate_api_token_masked}) — Paste new token to update` : "Paste r8_... token"}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500 font-mono text-xs"
                />
              </div>

              {/* DEEP RESEARCH TOGGLE */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
                <div className="space-y-0.5">
                  <span className="font-semibold text-slate-200">Gemini Deep Research Agent</span>
                  <p className="text-[11px] text-slate-400">Autonomous investigative research (takes ~2-5 min, ~$1-3 API cost).</p>
                </div>
                <input
                  type="checkbox"
                  checked={deepResearchToggle}
                  onChange={(e) => setDeepResearchToggle(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-700"
                />
              </div>
            </div>

            {/* MODAL FOOTER */}
            <div className="border-t border-slate-800 pt-4 flex items-center justify-between">
              <div className="text-[11px] text-slate-400">
                Keys are stored locally in <code className="text-slate-300">backend/.env</code> and never exposed.
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setShowSettingsModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveKeys}
                  disabled={isSavingKeys}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-bold text-xs flex items-center space-x-1.5 shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                >
                  {isSavingKeys ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving & Connecting...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Save & Connect Keys</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
