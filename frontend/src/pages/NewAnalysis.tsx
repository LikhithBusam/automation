import { useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Code2,
  Shield,
  FileText,
  Rocket,
  Search,
  TrendingUp,
  ArrowLeft,
  Upload,
  File,
  X,
  Plus,
  Zap,
  Clock,
  Users,
  Settings,
  ChevronDown,
  Play,
  DollarSign,
} from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import { workflowsApi } from '../lib/api'
import toast from 'react-hot-toast'

const workflows = [
  {
    id: 'quick_code_review',
    name: 'Quick Code Review',
    description: 'Fast code review for small changes. Perfect for PR reviews and quick checks.',
    icon: Code2,
    estimatedTime: '3-5s',
    agentCount: 2,
    category: 'quick' as const,
    color: 'from-blue-500 to-cyan-500',
    cost: '$0.01',
  },
  {
    id: 'security_audit',
    name: 'Security Audit',
    description: 'Deep vulnerability assessment following OWASP Top 10 guidelines.',
    icon: Shield,
    estimatedTime: '30-90s',
    agentCount: 3,
    category: 'comprehensive' as const,
    color: 'from-red-500 to-orange-500',
    cost: '$0.05',
  },
  {
    id: 'documentation_generation',
    name: 'Generate Docs',
    description: 'Generate or update project documentation automatically.',
    icon: FileText,
    estimatedTime: '10-30s',
    agentCount: 2,
    category: 'quick' as const,
    color: 'from-green-500 to-emerald-500',
    cost: '$0.02',
  },
  {
    id: 'deployment',
    name: 'Deployment Planning',
    description: 'Plan deployment strategy with Docker and Kubernetes configurations.',
    icon: Rocket,
    estimatedTime: '15-45s',
    agentCount: 2,
    category: 'comprehensive' as const,
    color: 'from-purple-500 to-pink-500',
    cost: '$0.03',
  },
  {
    id: 'code_analysis',
    name: 'Code Analysis',
    description: 'Comprehensive code analysis with security and quality checks.',
    icon: Search,
    estimatedTime: '20-60s',
    agentCount: 3,
    category: 'comprehensive' as const,
    color: 'from-indigo-500 to-blue-500',
    cost: '$0.04',
  },
  {
    id: 'research',
    name: 'Tech Research',
    description: 'Research technologies and get recommendations for your project.',
    icon: TrendingUp,
    estimatedTime: '20-60s',
    agentCount: 2,
    category: 'comprehensive' as const,
    color: 'from-amber-500 to-yellow-500',
    cost: '$0.03',
  },
]

const focusAreaSuggestions = [
  'Security',
  'Performance',
  'Error Handling',
  'Code Quality',
  'Best Practices',
  'Documentation',
  'Testing',
  'Accessibility',
  'Scalability',
  'Maintainability',
]

export default function NewAnalysis() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preselectedWorkflow = searchParams.get('workflow')

  const [step, setStep] = useState(preselectedWorkflow ? 2 : 1)
  const [selectedWorkflow, setSelectedWorkflow] = useState(
    workflows.find((w) => w.id === preselectedWorkflow) || null
  )
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [focusAreas, setFocusAreas] = useState<string[]>([])
  const [customFocusArea, setCustomFocusArea] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((f) => f.name)
    setSelectedFiles((prev) => [...new Set([...prev, ...newFiles])])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: false,
  })

  const handleWorkflowSelect = (workflow: typeof workflows[0]) => {
    setSelectedWorkflow(workflow)
    setStep(2)
  }

  const handleAddFocusArea = (area: string) => {
    if (!focusAreas.includes(area)) {
      setFocusAreas([...focusAreas, area])
    }
  }

  const handleRemoveFocusArea = (area: string) => {
    setFocusAreas(focusAreas.filter((a) => a !== area))
  }

  const handleCustomFocusAreaAdd = () => {
    if (customFocusArea.trim() && !focusAreas.includes(customFocusArea.trim())) {
      setFocusAreas([...focusAreas, customFocusArea.trim()])
      setCustomFocusArea('')
    }
  }

  const handleSubmit = async () => {
    if (!selectedWorkflow) return
    
    setIsSubmitting(true)
    try {
      // Call real API to start analysis
      const response = await workflowsApi.startAnalysis({
        workflowId: selectedWorkflow.id,
        files: selectedFiles,
        focusAreas: focusAreas,
        options: {}
      })
      
      toast.success('Analysis started!')
      
      // Navigate to results page with real job ID
      navigate(`/analysis/${response.data.id}`)
    } catch (error) {
      console.error('Failed to start analysis:', error)
      toast.error('Failed to start analysis. Make sure the backend is running.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => (step > 1 ? setStep(step - 1) : navigate('/'))}
          >
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-100)]">New Analysis</h1>
            <p className="text-sm text-[var(--color-gray-400)]">
              Step {step} of 2 {step === 1 ? '— Choose workflow' : '— Configure & Run'}
            </p>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center gap-2">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium ${
              step >= 1
                ? 'bg-[var(--color-primary-500)] text-white'
                : 'bg-[var(--bg-tertiary)] text-[var(--color-gray-500)]'
            }`}
          >
            1
          </div>
          <div className="h-0.5 w-8 bg-[var(--bg-tertiary)]">
            <div
              className={`h-full bg-[var(--color-primary-500)] transition-all ${
                step >= 2 ? 'w-full' : 'w-0'
              }`}
            />
          </div>
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium ${
              step >= 2
                ? 'bg-[var(--color-primary-500)] text-white'
                : 'bg-[var(--bg-tertiary)] text-[var(--color-gray-500)]'
            }`}
          >
            2
          </div>
        </div>
      </div>

      {/* Step 1: Workflow Selection */}
      <AnimatePresence mode="wait">
        {step === 1 && (
          <motion.div
            key="step1"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {workflows.map((workflow, index) => {
                const Icon = workflow.icon
                const isSelected = selectedWorkflow?.id === workflow.id

                return (
                  <motion.div
                    key={workflow.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => handleWorkflowSelect(workflow)}
                    className={`group cursor-pointer rounded-2xl border p-5 transition-all duration-300 ${
                      isSelected
                        ? 'border-[var(--color-primary-500)] bg-[var(--color-primary-500)]/10'
                        : 'border-[var(--glass-border)] bg-[var(--bg-secondary)] hover:border-[var(--color-primary-500)]/50'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${workflow.color} shadow-lg`}
                      >
                        <Icon className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-[var(--color-gray-100)]">
                            {workflow.name}
                          </h3>
                          {workflow.category === 'quick' && (
                            <Badge variant="success" size="sm">
                              <Zap className="h-3 w-3" />
                              Fast
                            </Badge>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-[var(--color-gray-400)]">
                          {workflow.description}
                        </p>
                        <div className="mt-3 flex items-center gap-4 text-xs text-[var(--color-gray-500)]">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {workflow.estimatedTime}
                          </span>
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {workflow.agentCount} agents
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3" />
                            ~{workflow.cost}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Step 2: Configuration */}
        {step === 2 && selectedWorkflow && (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            {/* Selected Workflow Summary */}
            <Card className="border-[var(--color-primary-500)]/30 bg-[var(--color-primary-500)]/5">
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${selectedWorkflow.color} shadow-lg`}
                >
                  <selectedWorkflow.icon className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-[var(--color-gray-100)]">
                    {selectedWorkflow.name}
                  </h3>
                  <p className="text-sm text-[var(--color-gray-400)]">
                    {selectedWorkflow.description}
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
                  Change
                </Button>
              </div>
            </Card>

            {/* File Selection */}
            <Card>
              <CardHeader>
                <CardTitle>Select Files</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  {...getRootProps()}
                  className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                    isDragActive
                      ? 'border-[var(--color-primary-500)] bg-[var(--color-primary-500)]/10'
                      : 'border-[var(--glass-border)] hover:border-[var(--color-primary-500)]/50'
                  }`}
                >
                  <input {...getInputProps()} />
                  <Upload className="mx-auto h-10 w-10 text-[var(--color-gray-500)]" />
                  <p className="mt-3 text-[var(--color-gray-300)]">
                    {isDragActive
                      ? 'Drop files here...'
                      : 'Drag & drop files here, or click to browse'}
                  </p>
                  <p className="mt-1 text-sm text-[var(--color-gray-500)]">
                    Supports Python, JavaScript, TypeScript, and more
                  </p>
                </div>

                {/* Selected Files */}
                {selectedFiles.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-sm text-[var(--color-gray-400)]">
                      {selectedFiles.length} file(s) selected
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedFiles.map((file) => (
                        <div
                          key={file}
                          className="flex items-center gap-2 rounded-lg bg-[var(--bg-tertiary)] px-3 py-1.5"
                        >
                          <File className="h-3.5 w-3.5 text-[var(--color-gray-500)]" />
                          <span className="text-sm text-[var(--color-gray-300)]">{file}</span>
                          <button
                            onClick={() => setSelectedFiles(selectedFiles.filter((f) => f !== file))}
                            className="text-[var(--color-gray-500)] hover:text-[var(--color-gray-300)]"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Focus Areas */}
            <Card>
              <CardHeader>
                <CardTitle>Focus Areas (Optional)</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-4 text-sm text-[var(--color-gray-400)]">
                  Select what aspects you want to focus on:
                </p>

                {/* Suggestions */}
                <div className="flex flex-wrap gap-2">
                  {focusAreaSuggestions.map((area) => {
                    const isSelected = focusAreas.includes(area)
                    return (
                      <button
                        key={area}
                        onClick={() =>
                          isSelected ? handleRemoveFocusArea(area) : handleAddFocusArea(area)
                        }
                        className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                          isSelected
                            ? 'bg-[var(--color-primary-500)] text-white'
                            : 'bg-[var(--bg-tertiary)] text-[var(--color-gray-400)] hover:text-[var(--color-gray-100)]'
                        }`}
                      >
                        {area}
                      </button>
                    )
                  })}
                </div>

                {/* Custom Input */}
                <div className="mt-4 flex gap-2">
                  <input
                    type="text"
                    value={customFocusArea}
                    onChange={(e) => setCustomFocusArea(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleCustomFocusAreaAdd()}
                    placeholder="Add custom focus area..."
                    className="flex-1 rounded-lg border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-2 text-sm text-[var(--color-gray-100)] placeholder-[var(--color-gray-500)] outline-none focus:border-[var(--color-primary-500)]"
                  />
                  <Button variant="secondary" size="sm" onClick={handleCustomFocusAreaAdd}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Advanced Options */}
            <Card>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex w-full items-center justify-between p-6"
              >
                <div className="flex items-center gap-3">
                  <Settings className="h-5 w-5 text-[var(--color-gray-400)]" />
                  <span className="font-medium text-[var(--color-gray-200)]">Advanced Options</span>
                </div>
                <ChevronDown
                  className={`h-5 w-5 text-[var(--color-gray-400)] transition-transform ${
                    showAdvanced ? 'rotate-180' : ''
                  }`}
                />
              </button>
              <AnimatePresence>
                {showAdvanced && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="space-y-4 border-t border-[var(--glass-border)] p-6">
                      {/* LLM Provider */}
                      <div>
                        <label className="mb-2 block text-sm text-[var(--color-gray-400)]">
                          LLM Provider
                        </label>
                        <select className="w-full rounded-lg border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-2 text-sm text-[var(--color-gray-100)] outline-none focus:border-[var(--color-primary-500)]">
                          <option value="openrouter">OpenRouter (Default)</option>
                          <option value="groq">Groq</option>
                          <option value="gemini">Google Gemini</option>
                        </select>
                      </div>

                      {/* Temperature */}
                      <div>
                        <label className="mb-2 block text-sm text-[var(--color-gray-400)]">
                          Temperature: 0.3
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          defaultValue="0.3"
                          className="w-full"
                        />
                      </div>

                      {/* Verbosity */}
                      <div>
                        <label className="mb-2 block text-sm text-[var(--color-gray-400)]">
                          Output Verbosity
                        </label>
                        <div className="flex gap-2">
                          {['Concise', 'Detailed', 'Comprehensive'].map((level) => (
                            <button
                              key={level}
                              className="flex-1 rounded-lg bg-[var(--bg-tertiary)] px-4 py-2 text-sm text-[var(--color-gray-400)] transition-colors hover:text-[var(--color-gray-100)]"
                            >
                              {level}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>

            {/* Submit Button */}
            <Card className="sticky bottom-4 border-[var(--color-primary-500)]/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[var(--color-gray-400)]">
                    Estimated time: <span className="font-medium text-[var(--color-gray-200)]">{selectedWorkflow.estimatedTime}</span>
                  </p>
                  <p className="text-sm text-[var(--color-gray-400)]">
                    Estimated cost: <span className="font-medium text-[var(--color-gray-200)]">{selectedWorkflow.cost}</span>
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={handleSubmit}
                  isLoading={isSubmitting}
                  leftIcon={<Play className="h-5 w-5" />}
                  disabled={selectedFiles.length === 0}
                >
                  Run Analysis
                </Button>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
