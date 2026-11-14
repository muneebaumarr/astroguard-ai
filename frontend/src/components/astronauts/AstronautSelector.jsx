export function AstronautSelector({ astronauts, selectedId, onSelect, disabled }) {
  return <div className="profile-select">
    <label htmlFor="astronaut-select">CREW PROFILE</label>
    <select id="astronaut-select" value={selectedId} onChange={event => onSelect(event.target.value)} disabled={disabled || !astronauts.length}>
      {!astronauts.length && <option value="">No crew available</option>}
      {astronauts.map(astronaut => <option key={astronaut.id} value={astronaut.id}>{astronaut.display_name}</option>)}
    </select>
  </div>
}
