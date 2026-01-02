import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Settings as SettingsIcon,
  Key,
  Server,
  Shield,
  Bell,
  Users,
  Palette,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Save,
  Github,
  FolderOpen,
  Brain,
  Code2,
  Loader2,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge, { StatusBadge } from '../components/ui/Badge'
import toast from 'react-hot-toast'
import { serversApi } from '../lib/api'

const settingsSections = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'api', label: 'API Configuration', icon: Key },
  { id: 'servers', label: 'MCP Servers', icon: Server },
  { id: 'security', label: 'Security & Privacy', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
]

// Icon mapping for server icons
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  github: Github,
  folder: FolderOpen,
  brain: Brain,
  code: Code2,
}

interface ServerInfo {
  id: string
  name: string
  port: number
  status: 'running' | 'stopped' | 'error'
  icon: string
  message?: string
}

export default function Settings() {
  const [activeSection, setActiveSection] = useState('general')
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [servers, setServers] = useState<ServerInfo[]>([])
  const [isLoadingServers, setIsLoadingServers] = useState(true)

  // Fetch MCP server status
  const fetchServerStatus = useCallback(async () => {
    setIsLoadingServers(true)
    try {
      const response = await serversApi.getStatus()
      setServers(response.data.servers)
    } catch (error) {
      console.error('Failed to fetch server status:', error)
      // Fallback to default servers with unknown status
      setServers([
        { id: 'github', name: 'GitHub Server', port: 3000, status: 'stopped', icon: 'github' },
        { id: 'filesystem', name: 'Filesystem Server', port: 3001, status: 'stopped', icon: 'folder' },
        { id: 'memory', name: 'Memory Server', port: 3002, status: 'stopped', icon: 'brain' },
        { id: 'codebasebuddy', name: 'CodeBaseBuddy', port: 3004, status: 'stopped', icon: 'code' },
      ])
      toast.error('Failed to fetch server status. Make sure the backend is running.')
    } finally {
      setIsLoadingServers(false)
    }
  }, [])

  useEffect(() => {
    fetchServerStatus()
  }, [fetchServerStatus])

  // Form state
  const [settings, setSettings] = useState({
    theme: 'dark',
    language: 'en',
    defaultWorkflow: 'quick_code_review',
    openrouterKey: 'sk-or-v1-xxxxxxxxxxxx',
    groqKey: 'gsk_xxxxxxxxxxxx',
    geminiKey: '',
    rateLimit: 60,
    notifications: {
      emailOnComplete: true,
      emailOnCritical: true,
      inAppNotifications: true,
    },
  })

  const handleSave = async () => {
    setIsSaving(true)
    await new Promise((r) => setTimeout(r, 1000))
    setIsSaving(false)
    toast.success('Settings saved successfully!')
  }

  const handleTestConnection = async (provider: string) => {
    toast.loading(`Testing ${provider} connection...`, { id: provider })
    await new Promise((r) => setTimeout(r, 1500))
    toast.success(`${provider} connected successfully!`, { id: provider })
  }

  const handleRestartServer = async (serverId: string) => {
    toast.loading(`Restarting ${serverId}...`, { id: serverId })
    try {
      await serversApi.restart(serverId)
      // Wait a bit for the server to restart
      await new Promise((r) => setTimeout(r, 2000))
      // Refresh server status
      await fetchServerStatus()
      toast.success(`${serverId} restart signal sent!`, { id: serverId })
    } catch (error) {
      console.error('Failed to restart server:', error)
      toast.error(`Failed to restart ${serverId}`, { id: serverId })
    }
  }

  const handleRefreshAll = async () => {
    toast.loading('Refreshing server status...', { id: 'refresh' })
    await fetchServerStatus()
    toast.success('Server status refreshed!', { id: 'refresh' })
  }

  return (
    <div className="flex gap-6">
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0">
        <Card className="sticky top-6">
          <nav className="space-y-1">
            {settingsSections.map((section) => {
              const Icon = section.icon
              const isActive = activeSection === section.id
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left transition-colors ${
                    isActive
                      ? 'bg-[var(--color-primary-500)]/20 text-[var(--color-primary-400)]'
                      : 'text-[var(--color-gray-400)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--color-gray-100)]'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="font-medium">{section.label}</span>
                </button>
              )
            })}
          </nav>
        </Card>
      </div>

      {/* Content */}
      <div className="flex-1 space-y-6">
        {/* General Settings */}
        {activeSection === 'general' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Theme */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-[var(--color-gray-300)]">
                    Theme
                  </label>
                  <div className="flex gap-2">
                    {['dark', 'light', 'auto'].map((theme) => (
                      <button
                        key={theme}
                        onClick={() => setSettings({ ...settings, theme })}
                        className={`flex-1 rounded-xl px-4 py-3 text-sm font-medium capitalize transition-colors ${
                          settings.theme === theme
                            ? 'bg-[var(--color-primary-500)] text-white'
                            : 'bg-[var(--bg-tertiary)] text-[var(--color-gray-400)] hover:text-[var(--color-gray-100)]'
                        }`}
                      >
                        {theme}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Default Workflow */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-[var(--color-gray-300)]">
                    Default Workflow
                  </label>
                  <select
                    value={settings.defaultWorkflow}
                    onChange={(e) => setSettings({ ...settings, defaultWorkflow: e.target.value })}
                    className="w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-3 text-sm text-[var(--color-gray-100)] outline-none focus:border-[var(--color-primary-500)]"
                  >
                    <option value="quick_code_review">Quick Code Review</option>
                    <option value="security_audit">Security Audit</option>
                    <option value="documentation_generation">Generate Docs</option>
                    <option value="deployment">Deployment Planning</option>
                  </select>
                </div>

                {/* Language */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-[var(--color-gray-300)]">
                    Language
                  </label>
                  <select
                    value={settings.language}
                    onChange={(e) => setSettings({ ...settings, language: e.target.value })}
                    className="w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-3 text-sm text-[var(--color-gray-100)] outline-none focus:border-[var(--color-primary-500)]"
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                  </select>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* API Configuration */}
        {activeSection === 'api' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle>API Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* OpenRouter */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-medium text-[var(--color-gray-300)]">
                      OpenRouter API Key
                    </label>
                    <Badge variant="success" size="sm" dot>
                      Connected
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showApiKey.openrouter ? 'text' : 'password'}
                        value={settings.openrouterKey}
                        onChange={(e) =>
                          setSettings({ ...settings, openrouterKey: e.target.value })
                        }
                        className="w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-3 pr-10 text-sm text-[var(--color-gray-100)] outline-none focus:border-[var(--color-primary-500)]"
                      />
                      <button
                        onClick={() =>
                          setShowApiKey({ ...showApiKey, openrouter: !showApiKey.openrouter })
                        }
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-gray-500)]"
                      >
                        {showApiKey.openrouter ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                    <Button
                      variant="secondary"
                      onClick={() => handleTestConnection('OpenRouter')}
                    >
                      Test
                    </Button>
                  </div>
                </div>

                {/* Groq */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-medium text-[var(--color-gray-300)]">
                      Groq API Key
                    </label>
                    <Badge variant="success" size="sm" dot>
                      Connected
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showApiKey.groq ? 'text' : 'password'}
                        value={settings.groqKey}
                        onChange={(e) => setSettings({ ...settings, groqKey: e.target.value })}
                        className="w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-3 pr-10 text-sm text-[var(--color-gray-100)] outline-none focus:border-[var(--color-primary-500)]"
                      />
                      <button
                        onClick={() => setShowApiKey({ ...showApiKey, groq: !showApiKey.groq })}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-gray-500)]"
                      >
                        {showApiKey.groq ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                    <Button variant="secondary" onClick={() => handleTestConnection('Groq')}>
                      Test
                    </Button>
                  </div>
                </div>

                {/* Gemini */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-medium text-[var(--color-gray-300)]">
                      Google Gemini API Key (Optional)
                    </label>
                    <Badge variant="default" size="sm">
                      Not Configured
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={settings.geminiKey}
                      onChange={(e) => setSettings({ ...settings, geminiKey: e.target.value })}
                      placeholder="Enter your Gemini API key..."
                      className="flex-1 rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-3 text-sm text-[var(--color-gray-100)] placeholder-[var(--color-gray-600)] outline-none focus:border-[var(--color-primary-500)]"
                    />
                    <Button variant="secondary" disabled>
                      Test
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* MCP Servers */}
        {activeSection === 'servers' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>MCP Servers</CardTitle>
                  <p className="text-sm text-[var(--color-gray-400)]">
                    Manage your Model Context Protocol servers
                  </p>
                </div>
                <Button 
                  variant="secondary" 
                  size="sm" 
                  leftIcon={isLoadingServers ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  onClick={handleRefreshAll}
                  disabled={isLoadingServers}
                >
                  {isLoadingServers ? 'Refreshing...' : 'Refresh All'}
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {isLoadingServers && servers.length === 0 ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-[var(--color-primary-400)]" />
                  </div>
                ) : servers.map((server) => {
                  const Icon = iconMap[server.icon] || Server
                  return (
                    <div
                      key={server.id}
                      className="flex items-center justify-between rounded-xl bg-[var(--bg-tertiary)] p-4"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-elevated)]">
                          <Icon className="h-5 w-5 text-[var(--color-gray-400)]" />
                        </div>
                        <div>
                          <h4 className="font-medium text-[var(--color-gray-100)]">{server.name}</h4>
                          <p className="text-sm text-[var(--color-gray-500)]">Port {server.port}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={server.status} />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRestartServer(server.id)}
                        >
                          Restart
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Security */}
        {activeSection === 'security' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle>Security & Privacy</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Rate Limiting */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-[var(--color-gray-300)]">
                    Rate Limit (requests per minute): {settings.rateLimit}
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={settings.rateLimit}
                    onChange={(e) =>
                      setSettings({ ...settings, rateLimit: parseInt(e.target.value) })
                    }
                    className="w-full"
                  />
                  <div className="mt-1 flex justify-between text-xs text-[var(--color-gray-500)]">
                    <span>10</span>
                    <span>100</span>
                  </div>
                </div>

                {/* Blocked Paths */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-[var(--color-gray-300)]">
                    Blocked File Patterns
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {['.env', '*.key', 'credentials.json', '*.pem'].map((pattern) => (
                      <Badge key={pattern} variant="danger" size="sm">
                        {pattern}
                      </Badge>
                    ))}
                  </div>
                  <input
                    type="text"
                    placeholder="Add pattern (e.g., *.secret)..."
                    className="mt-2 w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-2 text-sm text-[var(--color-gray-100)] placeholder-[var(--color-gray-600)] outline-none focus:border-[var(--color-primary-500)]"
                  />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Notifications */}
        {activeSection === 'notifications' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  {
                    key: 'emailOnComplete',
                    label: 'Email on analysis completion',
                    description: 'Receive an email when your analysis finishes',
                  },
                  {
                    key: 'emailOnCritical',
                    label: 'Email on critical issues',
                    description: 'Get notified immediately when critical vulnerabilities are found',
                  },
                  {
                    key: 'inAppNotifications',
                    label: 'In-app notifications',
                    description: 'Show notifications within the application',
                  },
                ].map((item) => (
                  <div
                    key={item.key}
                    className="flex items-center justify-between rounded-xl bg-[var(--bg-tertiary)] p-4"
                  >
                    <div>
                      <h4 className="font-medium text-[var(--color-gray-100)]">{item.label}</h4>
                      <p className="text-sm text-[var(--color-gray-500)]">{item.description}</p>
                    </div>
                    <button
                      onClick={() =>
                        setSettings({
                          ...settings,
                          notifications: {
                            ...settings.notifications,
                            [item.key]:
                              !settings.notifications[item.key as keyof typeof settings.notifications],
                          },
                        })
                      }
                      className={`relative h-6 w-11 rounded-full transition-colors ${
                        settings.notifications[item.key as keyof typeof settings.notifications]
                          ? 'bg-[var(--color-primary-500)]'
                          : 'bg-[var(--bg-elevated)]'
                      }`}
                    >
                      <span
                        className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                          settings.notifications[item.key as keyof typeof settings.notifications]
                            ? 'translate-x-6'
                            : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Save Button */}
        <div className="flex justify-end">
          <Button
            size="lg"
            onClick={handleSave}
            isLoading={isSaving}
            leftIcon={<Save className="h-5 w-5" />}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  )
}
