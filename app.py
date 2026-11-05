                        quantite_panier = 0
 
 
 
                        for produit_panier in (
 
                            st.session_state.panier
 
                        ):
 
                            if (
 
                                produit_panier["produit"]
 
                                == nom_produit(row)
 
                            ):
 
                                quantite_panier = (
 
                                    produit_panier["quantite"]
 
                                )
 
                                break
 
 
 
                        stock_restant_affichable = max(
 
                            0,
 
                            stock_dispo - quantite_panier
 
                        )
 
 
 
                        st.caption(
 
                            f"Stock disponible : "
 
                            f"{stock_restant_affichable}"
 
                        )
 
 
 
                        bouton_desactive = (
 
                            quantite_panier >= stock_dispo
 
                        )
 
 
 
                        if st.button(
 
                            "➕ Ajouter",
 
                            key=f"add_{row.name}_{index}",
 
                            width="stretch",
 
                            disabled=bouton_desactive
 
                        ):
 
                            ajouter_au_panier(row)
 
 
 
                            st.toast(
 
                                f"Ajouté : "
 
                                f"{nom_produit(row)}"
 
                            )
 
 
 
                            st.rerun()
 
 
 
                    st.markdown(
 
                        "<br>",
 
                        unsafe_allow_html=True
 
                    )
 
 
 
    except Exception as e:
 
        st.error(
 
            f"Erreur d'initialisation de la base produit : {e}"
 
        )
