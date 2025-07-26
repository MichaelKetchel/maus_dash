/**
 * Module management service for interacting with enhanced module API
 */

class ModuleService {
  constructor() {
    this.baseUrl = '/api/modules'
  }

  /**
   * Get all modules with detailed information
   */
  async getModules() {
    try {
      const response = await fetch(this.baseUrl)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching modules:', error)
      throw error
    }
  }

  /**
   * Reload a specific module
   * @param {string} moduleName - Name of the module to reload
   * @param {boolean} force - Force reload even if no changes detected
   */
  async reloadModule(moduleName, force = false) {
    try {
      const url = `${this.baseUrl}/${moduleName}/reload${force ? '?force=true' : ''}`
      const response = await fetch(url, { method: 'POST' })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error(`Error reloading module ${moduleName}:`, error)
      throw error
    }
  }

  /**
   * Unload a specific module
   * @param {string} moduleName - Name of the module to unload
   * @param {boolean} force - Force unload even with dependencies
   */
  async unloadModule(moduleName, force = false) {
    try {
      const url = `${this.baseUrl}/${moduleName}/unload${force ? '?force=true' : ''}`
      const response = await fetch(url, { method: 'POST' })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error(`Error unloading module ${moduleName}:`, error)
      throw error
    }
  }

  /**
   * Reload all modules
   * @param {boolean} force - Force reload all modules
   */
  async reloadAllModules(force = false) {
    try {
      const url = `${this.baseUrl}/reload-all${force ? '?force=true' : ''}`
      const response = await fetch(url, { method: 'POST' })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error reloading all modules:', error)
      throw error
    }
  }

  /**
   * Auto-reload modules with file changes
   */
  async autoReloadModules() {
    try {
      const response = await fetch(`${this.baseUrl}/auto-reload`, { method: 'POST' })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error auto-reloading modules:', error)
      throw error
    }
  }

  /**
   * Check for module file changes
   */
  async checkModuleChanges() {
    try {
      const response = await fetch(`${this.baseUrl}/changes`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error checking module changes:', error)
      throw error
    }
  }

  /**
   * Get module dependency graph
   */
  async getDependencyGraph() {
    try {
      const response = await fetch(`${this.baseUrl}/dependency-graph`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error fetching dependency graph:', error)
      throw error
    }
  }

  /**
   * Get all module routes
   */
  async getModuleRoutes() {
    try {
      const response = await fetch(`${this.baseUrl}/routes`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error fetching module routes:', error)
      throw error
    }
  }

  /**
   * Get formatted module state display
   * @param {string} state - Module state
   */
  getStateInfo(state) {
    const stateMap = {
      'unloaded': { color: 'gray', label: 'Unloaded', icon: 'circle' },
      'loading': { color: 'yellow', label: 'Loading...', icon: 'loader' },
      'loaded': { color: 'blue', label: 'Loaded', icon: 'circle' },
      'initializing': { color: 'orange', label: 'Initializing...', icon: 'loader' },
      'ready': { color: 'green', label: 'Ready', icon: 'check-circle' },
      'error': { color: 'red', label: 'Error', icon: 'alert-circle' },
      'unloading': { color: 'yellow', label: 'Unloading...', icon: 'loader' }
    }
    
    return stateMap[state] || { color: 'gray', label: 'Unknown', icon: 'help-circle' }
  }

  /**
   * Format module name for display
   * @param {string} name - Module name
   */
  formatModuleName(name) {
    return name.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ')
  }

  /**
   * Get module API documentation URL
   * @param {string} moduleName - Module name
   */
  getModuleDocsUrl(moduleName) {
    return `/docs#/operations/tag:${moduleName}`
  }
}

// Export singleton instance
export const moduleService = new ModuleService()
export default moduleService