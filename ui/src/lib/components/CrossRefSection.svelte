<script lang="ts">
	import { selectedVerse, selectVerse } from '$lib/stores/selection';
	import { getCached, setCached, crossRefsKey } from '$lib/stores/cache';
	import { findCrossReferences } from '$lib/api/ollama';
	import { searchBible } from '$lib/api/prism';
	import { ChevronDown, ChevronRight, Link2, RefreshCw } from 'lucide-svelte';
	import type { CrossReference } from '$lib/types/bible';

	let expanded = false;
	let loading = false;
	let crossRefs: CrossReference[] = [];
	let error: string | null = null;

	$: if ($selectedVerse && expanded && crossRefs.length === 0) {
		loadCrossRefs();
	}

	async function loadCrossRefs() {
		if (!$selectedVerse) return;

		const cacheKey = crossRefsKey($selectedVerse.verse_ref);

		// Check cache first
		const cached = getCached<CrossReference[]>(cacheKey);
		if (cached) {
			crossRefs = cached;
			return;
		}

		loading = true;
		error = null;

		try {
			const result = await findCrossReferences(
				$selectedVerse.text,
				$selectedVerse.verse_ref
			);

			crossRefs = result;
			setCached(cacheKey, result);
		} catch (err) {
			console.error('Cross-reference generation failed:', err);
			error = 'Failed to find cross-references. Please try again.';
		} finally {
			loading = false;
		}
	}

	async function jumpToReference(ref: string) {
		try {
			// Search for the specific verse
			const results = await searchBible(ref, ['kjv'], 1);
			if (results.length > 0) {
				selectVerse(results[0]);
			}
		} catch (err) {
			console.error('Failed to jump to reference:', err);
		}
	}

	function toggle() {
		expanded = !expanded;
	}

	function getRelationIcon(type: string): string {
		const icons: Record<string, string> = {
			quote: '📖',
			thematic: '🔗',
			parallel: '⚖️',
			contrast: '↔️'
		};
		return icons[type] || '•';
	}

	// Reset when verse changes
	$: if ($selectedVerse) {
		crossRefs = [];
		error = null;
		expanded = false;
	}
</script>

<div class="crossref-section bg-white rounded-lg border border-gray-200 overflow-hidden">
	<!-- Header -->
	<button
		on:click={toggle}
		class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
	>
		<div class="flex items-center gap-2">
			<Link2 class="h-4 w-4 text-primary-600" />
			<h3 class="text-sm font-semibold text-gray-800">Cross-References</h3>
		</div>
		{#if expanded}
			<ChevronDown class="h-4 w-4 text-gray-400" />
		{:else}
			<ChevronRight class="h-4 w-4 text-gray-400" />
		{/if}
	</button>

	<!-- Content -->
	{#if expanded}
		<div class="border-t border-gray-200 bg-gray-50">
			{#if loading}
				<div class="px-4 py-3 flex items-center gap-2 text-sm text-gray-600">
					<RefreshCw class="h-4 w-4 animate-spin" />
					Finding cross-references...
				</div>
			{:else if error}
				<div class="px-4 py-3">
					<div class="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
						{error}
						<button
							on:click={loadCrossRefs}
							class="mt-2 text-red-700 hover:text-red-800 font-medium underline"
						>
							Retry
						</button>
					</div>
				</div>
			{:else if crossRefs.length > 0}
				<div class="divide-y divide-gray-200">
					{#each crossRefs as ref}
						<button
							on:click={() => jumpToReference(ref.verse_ref)}
							class="w-full px-4 py-3 text-left hover:bg-gray-100 transition-colors"
						>
							<div class="flex items-start gap-2">
								<span class="text-base mt-0.5">{getRelationIcon(ref.relation_type)}</span>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-semibold text-primary-700 hover:text-primary-800">
										{ref.verse_ref}
									</div>
									<p class="text-xs text-gray-600 mt-1">
										{ref.explanation}
									</p>
									<span class="text-xs text-gray-400 capitalize mt-1 inline-block">
										{ref.relation_type}
									</span>
								</div>
							</div>
						</button>
					{/each}
				</div>
			{:else}
				<div class="px-4 py-3">
					<button
						on:click={loadCrossRefs}
						class="w-full py-2 px-4 text-sm text-primary-700 bg-primary-50 hover:bg-primary-100
							   border border-primary-200 rounded-md transition-colors font-medium"
					>
						Find Cross-References
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
