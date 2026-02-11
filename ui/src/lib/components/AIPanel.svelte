<script lang="ts">
	import { selectedVerse, comparisonData } from '$lib/stores/selection';
	import { Sparkles } from 'lucide-svelte';
	import CommentarySection from './CommentarySection.svelte';
	import CrossRefSection from './CrossRefSection.svelte';
	import TranslationInsightsSection from './TranslationInsightsSection.svelte';
</script>

<div class="ai-panel h-full flex flex-col bg-gray-50 border-l border-gray-200 overflow-y-auto">
	<!-- Header -->
	<div class="sticky top-0 z-10 px-5 py-4 bg-white border-b border-gray-200">
		<h2 class="text-base font-bold text-gray-700 flex items-center gap-2">
			<Sparkles class="h-4 w-4 text-primary-600" />
			AI Insights
		</h2>
	</div>

	{#if !$selectedVerse}
		<!-- Empty state -->
		<div class="flex-1 flex items-center justify-center p-6">
			<div class="text-center text-gray-400">
				<Sparkles class="h-12 w-12 mx-auto mb-3 opacity-30" />
				<p class="text-sm">AI-generated insights will appear here</p>
				<p class="text-xs mt-2">Select a verse to begin</p>
			</div>
		</div>
	{:else}
		<!-- AI sections -->
		<div class="flex-1 p-5 space-y-4">
			<!-- Commentary section -->
			<CommentarySection />

			<!-- Cross-references section -->
			<CrossRefSection />

			<!-- Translation insights section (only if comparing multiple translations) -->
			{#if Object.keys($comparisonData).length > 1}
				<TranslationInsightsSection />
			{/if}
		</div>

		<!-- Footer with data provenance -->
		<div class="sticky bottom-0 px-5 py-4 bg-sand-50 border-t border-sand-200">
			<div class="bg-amber-50 rounded-lg p-3 border border-amber-200 mb-2">
				<h5 class="text-sm font-semibold text-amber-900 mb-1 flex items-center gap-1">
					<Sparkles class="h-3 w-3" />
					AI-Generated Content
				</h5>
				<p class="text-sm text-amber-800">
					These insights are for research exploration, not definitive interpretation.
					Always consult scholarly commentaries for authoritative analysis.
				</p>
			</div>
			<div class="text-sm text-gray-600">
				<p class="mb-1"><strong>AI Model:</strong> Qwen 2.5 14B (via Ollama)</p>
				<p><strong>Temperature:</strong> 0.7 (creative insights) • <strong>Cached:</strong> 1 hour TTL</p>
			</div>
		</div>
	{/if}
</div>

<style>
	.ai-panel {
		min-width: 320px;
		max-width: 400px;
	}

	/* Mobile responsive adjustments */
	@media (max-width: 767px) {
		.ai-panel {
			min-width: 100%;
			max-width: 100%;
		}
	}

	/* Tablet responsive adjustments */
	@media (min-width: 768px) and (max-width: 1023px) {
		.ai-panel {
			min-width: 280px;
			max-width: 320px;
		}
	}
</style>
