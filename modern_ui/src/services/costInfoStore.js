// Global cost information store that doesn't trigger React re-renders
class CostInfoStore {
  constructor() {
    this.costInfo = null;
    this.listeners = new Set();
  }

  setCostInfo(costInfo) {
    this.costInfo = costInfo;
    // Update DOM directly without triggering React re-renders
    this.updateDOM();
  }

  getCostInfo() {
    return this.costInfo;
  }

  addListener(callback) {
    this.listeners.add(callback);
  }

  removeListener(callback) {
    this.listeners.delete(callback);
  }

  updateDOM() {
    // Direct DOM manipulation to update cost information without React re-renders
    const modelElement = document.querySelector('[data-cost-info="model"]');
    const tokensElement = document.querySelector('[data-cost-info="tokens"]');
    const costElement = document.querySelector('[data-cost-info="cost"]');

    if (this.costInfo) {
      if (modelElement) {
        modelElement.textContent = `Model: ${this.costInfo.model || 'Unknown'}`;
      }
      if (tokensElement) {
        tokensElement.textContent = `Tokens: ${this.costInfo.tokens || '0'}`;
      }
      if (costElement) {
        costElement.textContent = `Cost: $${(this.costInfo.cost || 0).toFixed(3)}`;
      }
    }
  }
}

// Create a singleton instance
const costInfoStore = new CostInfoStore();

export default costInfoStore;
