# RRR Investments: website revamp ("From Seed to Banyan")

A scroll-driven story site. Blender-built 3D models are rendered live with three.js behind the page, and each chapter brings its own object on stage.

## Run
```
npm install
npm run dev      # http://localhost:5180
npm run build    # static output in dist/ (deploy anywhere: Vercel, Netlify, S3)
```

## The story
| Chapter | Section | 3D object | Idea |
|---|---|---|---|
| Prologue | Hero | RRR monolith (the logo's three blades) | Invest with Purpose. Grow with Strategy. |
| I · Bīja (seed) | Philosophy, values, differentiators | Monolith | Ethics, innovation, courage, intuition |
| II · Śravaṇa | Market signals | Shankha (conch) | Listen: hear the market before it speaks |
| II · Manana | Company validation | Urli (brass bowl + still water) | Question: let the noise settle |
| II · Nididhyāsana | On-ground evidence | Diya (oil lamp) | Know: conviction is earned |
| III · C.O.R.E | Framework | Monolith blades split apart | Four lenses |
| IV · Vaṭa (banyan) | Portfolio | Banyan: 20 nodes light up as you scroll | Compounding; 15–25 holdings |
| V · The fund | Strategic Growth Fund, team, Club RRR, insights, careers, contact | Monolith / diya | |

## Where things live
- `index.html`: all page copy
- `src/style.css`: design tokens (`:root`) and layout
- `src/main.js`: smooth scroll (Lenis), GSAP reveals, scene switching, team/insights fetch, contact form
- `src/scene.js`: three.js stage. `STATES` sets where each model stands per chapter (`data-scene` on sections)
- `src/content.js`: static fallback for team and posts (refreshed live from `api.rrrinvestments.in`)
- `blender/`: Python scripts that build every model (see `blender/README.md`)
- `public/models/*.glb`, `public/renders/*` (og.jpg is the social share image)

The contact form posts to the existing endpoint `POST /api/website/contacts/inquiries/submit` with `{ responses: { fullName, email, phoneNumber, yourQuery } }`. Your API's CORS settings must allow the new domain.
