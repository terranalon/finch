import { ibkrGuide } from './ibkr.js';
import { krakenGuide } from './kraken.js';

export const BROKER_GUIDES = {
  ibkr: ibkrGuide,
  kraken: krakenGuide,
};

export function getBrokerGuide(brokerType, guideType) {
  return BROKER_GUIDES[brokerType]?.[guideType] ?? null;
}
