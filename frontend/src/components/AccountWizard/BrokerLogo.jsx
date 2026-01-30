import { cn } from '../../lib';

const BROKER_LOGOS = {
  ibkr: 'https://cdn.brandfetch.io/idcABCQwX-/w/400/h/400/theme/dark/icon.jpeg',
  meitav: 'https://cdn.brandfetch.io/idT29sW48-/w/400/h/400/theme/dark/logo.png',
  kraken: 'https://cdn.brandfetch.io/idYQrXoH-Q/w/400/h/400/theme/dark/symbol.png',
  bit2c: 'https://cdn.brandfetch.io/idatfQiwS7/w/400/h/400/theme/dark/icon.jpeg',
  binance: 'https://cdn.brandfetch.io/id-pjrLx_q/w/400/h/400/theme/dark/symbol.png',
};

export function BrokerLogo({ type, className = 'size-12' }) {
  const logoUrl = BROKER_LOGOS[type];

  if (!logoUrl) {
    return (
      <div className={cn(className, 'flex items-center justify-center')}>
        <span className="text-gray-500 dark:text-gray-400 font-bold text-sm">
          {type?.toUpperCase()?.slice(0, 4)}
        </span>
      </div>
    );
  }

  return (
    <img
      src={logoUrl}
      alt={`${type} logo`}
      className={cn(className, 'object-contain')}
      loading="lazy"
    />
  );
}
