export function Footer() {
  return (
    <footer className="bg-dark-surface border-t border-dark-border py-4 px-6 mt-auto">
      <div className="container mx-auto flex items-center justify-between text-sm text-dark-muted">
        <div>
          <span className="font-semibold text-dark-text">Sentiment Arena</span> - AI Trading Competition
        </div>
        <div className="flex items-center space-x-4">
          <span>Paper Trading Only</span>
          <span>•</span>
          <span>German Stocks (XETRA/DAX)</span>
          <span>•</span>
          <span className="text-xs">v1.0.0</span>
        </div>
      </div>
    </footer>
  )
}
