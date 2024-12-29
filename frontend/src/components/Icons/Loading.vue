<template>
	<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24">
		<circle
			v-for="(begin, index) in [0, 0.33, 0.67]"
			:key="index"
			:cx="6 + index * 6"
			cy="12"
			r="0"
			fill="currentColor">
			<animate
				attributeName="r"
				:begin="begin"
				calcMode="spline"
				dur="1.5s"
				keySplines="0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8"
				repeatCount="indefinite"
				values="0;2;0;0" />
		</circle>
	</svg>
</template>
