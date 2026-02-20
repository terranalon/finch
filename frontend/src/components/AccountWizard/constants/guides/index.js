/**
 * Registry of rich setup guides for each broker.
 *
 * When a broker has a rich guide, the SetupGuidePanel renders the enhanced
 * layout (screenshots, tips, data scope, troubleshooting). For brokers not
 * yet in this registry, the panel falls back to the simple step list from
 * brokerConfig.js instructions.
 */

import { krakenGuide } from './kraken.js';

export const BROKER_GUIDES = {
  kraken: krakenGuide,
};

/**
 * Get the rich guide data for a broker + guide type (api / file).
 * Returns null if no rich guide is available (panel should use fallback).
 */
export function getBrokerGuide(brokerType, guideType) {
  return BROKER_GUIDES[brokerType]?.[guideType] ?? null;
}
