import SwiftUI

struct CreditsView: View {
    let credits: [CreditLine]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(credits) { line in
                    Text(line.text)
                        .font(.title3)
                }
            }
            .padding(40)
        }
    }
}

struct CreditLine: Identifiable, Hashable {
    let id: UUID
    let text: String
}
