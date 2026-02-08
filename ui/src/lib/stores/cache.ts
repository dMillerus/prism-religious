// LLM response caching to avoid re-generation

import { writable } from 'svelte/store';

interface CacheEntry<T> {
	data: T;
	timestamp: number;
}

type CacheStore = Record<string, CacheEntry<any>>;

// Cache store
const cache = writable<CacheStore>({});

/**
 * Get cached value if still valid
 * @param key Cache key
 * @param maxAge Maximum age in milliseconds (default 1 hour)
 * @returns Cached data or null if expired/missing
 */
export function getCached<T>(key: string, maxAge: number = 3600000): T | null {
	let cachedValue: CacheEntry<T> | undefined;

	cache.subscribe(c => {
		cachedValue = c[key];
	})();  // Immediately unsubscribe

	if (cachedValue && Date.now() - cachedValue.timestamp < maxAge) {
		console.log(`Cache hit: ${key}`);
		return cachedValue.data;
	}

	console.log(`Cache miss: ${key}`);
	return null;
}

/**
 * Set cached value
 * @param key Cache key
 * @param data Data to cache
 */
export function setCached<T>(key: string, data: T): void {
	cache.update(c => ({
		...c,
		[key]: {
			data,
			timestamp: Date.now()
		}
	}));
	console.log(`Cached: ${key}`);
}

/**
 * Clear specific cache entry
 */
export function clearCache(key: string): void {
	cache.update(c => {
		const updated = { ...c };
		delete updated[key];
		return updated;
	});
}

/**
 * Clear all cache entries
 */
export function clearAllCache(): void {
	cache.set({});
	console.log('All cache cleared');
}

/**
 * Clear expired cache entries
 * @param maxAge Maximum age in milliseconds
 */
export function clearExpiredCache(maxAge: number = 3600000): void {
	const now = Date.now();
	cache.update(c => {
		const updated: CacheStore = {};
		let clearedCount = 0;

		Object.entries(c).forEach(([key, entry]) => {
			if (now - entry.timestamp < maxAge) {
				updated[key] = entry;
			} else {
				clearedCount++;
			}
		});

		console.log(`Cleared ${clearedCount} expired cache entries`);
		return updated;
	});
}

/**
 * Generate cache key for commentary
 */
export function commentaryKey(reference: string, translation: string): string {
	return `commentary:${reference}:${translation}`;
}

/**
 * Generate cache key for cross-references
 */
export function crossRefsKey(reference: string): string {
	return `crossrefs:${reference}`;
}

/**
 * Generate cache key for translation insights
 */
export function translationInsightsKey(reference: string, translations: string[]): string {
	return `transinsights:${reference}:${translations.sort().join(',')}`;
}

/**
 * Generate cache key for thematic summary
 */
export function thematicSummaryKey(query: string, resultCount: number): string {
	return `summary:${query}:${resultCount}`;
}

// Auto-cleanup expired cache every 10 minutes
if (typeof window !== 'undefined') {
	setInterval(() => {
		clearExpiredCache();
	}, 600000);  // 10 minutes
}
