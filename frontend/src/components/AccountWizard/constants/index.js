export {
  BROKER_CATEGORIES,
  BROKERS,
  getBrokersByCategory,
  getBrokerConfig,
  getInitialCredentials,
} from './brokerConfig';

/**
 * Account category identifiers.
 * Use these constants instead of magic strings.
 */
export const CATEGORY_IDS = {
  BROKERAGE: 'brokerage',
  CRYPTO: 'crypto',
  MANUAL: 'manual',
  LINK: 'link',
};
