module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'node_modules'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
  overrides: [
    {
      // shadcn primitives co-locate the *Variants helper with the component;
      // providers co-locate their context hook. Both are idiomatic.
      // Chart components co-locate small helpers (defaults, overlay keys)
      // with their component; shadcn primitives co-locate the *Variants helper;
      // providers co-locate their context hook. All idiomatic.
      files: [
        'src/components/ui/**/*.tsx',
        'src/components/charts/**/*.tsx',
        'src/providers/**/*.tsx',
      ],
      rules: { 'react-refresh/only-export-components': 'off' },
    },
  ],
};
