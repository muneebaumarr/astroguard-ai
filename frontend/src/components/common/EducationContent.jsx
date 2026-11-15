export const educationDisclaimer = 'General spaceflight education, not a diagnosis, treatment recommendation or mission response procedure. NASA sources describe research; fictional AstroGuard data and topic suggestions are not NASA-approved or clinically validated.'

export function EducationText({ text }) {
  return <div className="education-copy">{text.split('\n\n').map((paragraph, index) => {
    const separator = paragraph.indexOf(': ')
    return separator > 0 ? <section key={index}><h3>{paragraph.slice(0, separator)}</h3><p>{paragraph.slice(separator + 2)}</p></section> : <p key={index}>{paragraph}</p>
  })}</div>
}

export function EducationSources({ references, reviewedOn }) {
  return <div className="education-sources"><h3>Official educational sources</h3><ul>{references.map(source => <li key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title} ↗</a></li>)}</ul>
    {reviewedOn && <p>Content reviewed {reviewedOn}. Sources are external; browsing them requires internet access.</p>}</div>
}
