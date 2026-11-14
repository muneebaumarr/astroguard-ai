export function PageHeading({ eyebrow, title, children, aside }) {
  return <div className="page-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1><p>{children}</p></div>{aside}</div>
}
